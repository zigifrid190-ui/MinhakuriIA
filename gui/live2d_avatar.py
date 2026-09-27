"""Widget Live2D para o avatar da Kuri (PyQt6 + live2d-py)."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtGui import QCursor

from path_utils import get_resource_path
from gui.kuri_bridge import KuriState

_LIVE2D_READY = False
_LIVE2D_MODULE = None


def _ensure_live2d():
    global _LIVE2D_READY, _LIVE2D_MODULE
    if _LIVE2D_READY:
        return _LIVE2D_MODULE
    try:
        import live2d.v3 as live2d  # type: ignore

        live2d.init()
        _LIVE2D_MODULE = live2d
        _LIVE2D_READY = True
        return live2d
    except Exception:
        return None


def get_live2d_model_dir() -> Path:
    return Path(get_resource_path(os.path.join("assets", "live2d", "kuri_model")))


def is_live2d_model_available() -> bool:
    model_dir = get_live2d_model_dir()
    return (model_dir / "kuri.model3.json").exists()


def can_use_live2d_avatar() -> bool:
    return _ensure_live2d() is not None and is_live2d_model_available()


def shutdown_live2d():
    global _LIVE2D_READY, _LIVE2D_MODULE
    if _LIVE2D_READY and _LIVE2D_MODULE is not None:
        _LIVE2D_MODULE.dispose()
        _LIVE2D_READY = False
        _LIVE2D_MODULE = None


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class Live2DAvatarWidget(QOpenGLWidget):
    """Renderiza o modelo Live2D e reage às emoções da Kuri."""

    FPS_MAP = {
        "idle": 20,       # 50ms - respiração suave
        "listening": 30,  # 33ms - maior responsividade
        "thinking": 24,   # 41ms - animação leve
        "speaking": 30,   # 33ms - sincronia labial
        "error": 15,      # 67ms - baixo consumo
    }

    DEFAULT_FRAMING = {
        "min_height": 72,
        "max_height": 520,
        "scale": {"min": 3.0, "max": 1.9},
        "offset_x": {"min": 0.0, "max": 0.0},
        "offset_y": {"min": -2.5, "max": -1.2},
        "curve_power": 3.0,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._live2d = _ensure_live2d()
        self._model = None
        self._emotion_map: dict[str, str | None] = {}
        self._animation_map: dict = {}
        self._framing_config = dict(self.DEFAULT_FRAMING)
        self._current_emotion = "neutral"
        self._current_state = KuriState.IDLE
        self._state_expression: str | None = None
        self._procedural_params: dict = {}
        self._speaking = False
        self._tick = 0.0
        self._viewport_height = 0

        # Otimizações de CPU e Interação
        self._deep_idle = False
        self._deep_idle_timer = QTimer(self)
        self._deep_idle_timer.setSingleShot(True)
        self._deep_idle_timer.timeout.connect(self._enter_deep_idle)
        self._deep_idle_timer.start(5 * 60 * 1000)  # 5 minutos para repouso profundo

        # Animações
        self._blink_tick = 0
        self._waking_up = True
        self._wake_up_tick = 0
        self._speak_gesture_tick = 0
        self._current_angle_x = 0.0
        self._current_angle_y = 0.0
        self._current_eyeball_x = 0.0
        self._current_eyeball_y = 0.0
        self.use_mouse_tracking = True

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(33)

    def _reset_activity(self):
        """Acorda o avatar do deep idle e reinicia o cronômetro."""
        # Do not reset if we are in sleep mode
        if self._current_state == KuriState.SLEEPING:
            return
        if self._deep_idle:
            self._deep_idle = False
            self._set_fps(self._current_state.name.lower() if self._current_state else "idle")
        if hasattr(self, "_sleep_params"):
            delattr(self, "_sleep_params")
        self._deep_idle_timer.start(5 * 60 * 1000)

    def _enter_deep_idle(self):
        """Coloca o avatar em modo de hibernação a 1 FPS para economizar CPU."""
        self._deep_idle = True
        # No sono usamos intervalo ainda mais lento (2s = 0.5 FPS) para visual relaxado
        interval = 2000 if self._current_state == KuriState.SLEEPING else 1000
        self._timer.setInterval(interval)

    def _set_fps(self, state_name: str):
        """Ajusta o FPS conforme o estado ativo do avatar."""
        if self._deep_idle:
            return
        fps = self.FPS_MAP.get(state_name, 24)
        interval = int(1000 / fps)
        if self._timer.interval() != interval:
            self._timer.setInterval(interval)

    def trigger_speak_gesture(self):
        """Ativa um leve balanço de cabeça orgânico ao falar/receber texto."""
        self._reset_activity()
        self._speak_gesture_tick = 30  # ~1 segundo de duração a 30 FPS

    def _load_config(self):
        model_dir = get_live2d_model_dir()
        emotion_file = model_dir / "emotion_map.json"
        if emotion_file.exists():
            self._emotion_map = json.loads(emotion_file.read_text(encoding="utf-8"))

        animation_file = model_dir / "animation_map.json"
        if animation_file.exists():
            payload = json.loads(animation_file.read_text(encoding="utf-8"))
            self._animation_map = payload.get("states", {})
            if payload.get("emotion_expressions"):
                self._emotion_map = payload["emotion_expressions"]

        viewport_file = model_dir / "viewport_config.json"
        if viewport_file.exists():
            payload = json.loads(viewport_file.read_text(encoding="utf-8"))
            self._framing_config.update(payload.get("framing", {}))

    def initializeGL(self):
        if not self._live2d:
            return

        self._load_config()
        self._live2d.glInit()
        self._model = self._live2d.LAppModel()

        model_json = str(get_live2d_model_dir() / "kuri.model3.json")
        self._model.LoadModelJson(model_json)
        self._model.SetAutoBlinkEnable(False)
        self._model.SetAutoBreathEnable(True)

        self._current_state = None
        self.set_state(KuriState.IDLE)
        self._refresh_expression()
        self.update_framing(max(self.height(), 1))

    def update_framing(self, viewport_height: int):
        """Ajusta zoom e posição: pequeno = busto; grande = corpo inteiro."""
        self._viewport_height = max(1, viewport_height)
        if not self._model:
            return

        cfg = self._framing_config
        min_h = float(cfg.get("min_height", self.DEFAULT_FRAMING["min_height"]))
        max_h = float(cfg.get("max_height", self.DEFAULT_FRAMING["max_height"]))
        curve_power = float(cfg.get("curve_power", self.DEFAULT_FRAMING["curve_power"]))
        raw_t = _clamp((self._viewport_height - min_h) / max(max_h - min_h, 1.0), 0.0, 1.0)
        t = raw_t**curve_power

        scale_cfg = cfg.get("scale", self.DEFAULT_FRAMING["scale"])
        offset_x_cfg = cfg.get("offset_x", self.DEFAULT_FRAMING["offset_x"])
        offset_y_cfg = cfg.get("offset_y", self.DEFAULT_FRAMING["offset_y"])

        scale = _lerp(float(scale_cfg["min"]), float(scale_cfg["max"]), t)
        offset_x = _lerp(float(offset_x_cfg["min"]), float(offset_x_cfg["max"]), t)
        offset_y = _lerp(float(offset_y_cfg["min"]), float(offset_y_cfg["max"]), t)

        self._model.SetScale(scale)
        self._model.SetOffsetX(offset_x)
        self._model.SetOffsetY(offset_y)

    def resizeGL(self, width: int, height: int):
        if self._model:
            self._model.Resize(width, height)
            self.update_framing(height)

    def paintGL(self):
        if not self._live2d or not self._model:
            return

        self._model.Update()

        # Force sleep visual params after Update so they override any motion blending
        if self._current_state == KuriState.SLEEPING and hasattr(self, "_sleep_params"):
            sp = self._sleep_params
            try:
                self._model.StopAllMotions()
                self._model.SetParameterValue("ParamEyeLOpen", sp["ParamEyeLOpen"])
                self._model.SetParameterValue("ParamEyeROpen", sp["ParamEyeROpen"])
                if "ParamEyeLSmile" in sp:
                    self._model.SetParameterValue("ParamEyeLSmile", sp.get("ParamEyeLSmile", 0.2))
                    self._model.SetParameterValue("ParamEyeRSmile", sp.get("ParamEyeRSmile", 0.2))
                sway = math.sin(self._tick * 0.15) * 3.8
                self._model.SetParameterValue("ParamAngleY", sp["ParamAngleY"] + sway)
                breath = 0.5 + math.sin(self._tick * sp.get("breath_speed", 0.35)) * sp.get("breath_wave", 0.6) * 0.5
                self._model.SetParameterValue("ParamBreath", breath)

                # Orelhas + boquinha bem sutil no sono (só o que o artista já expôs)
                ear_sway = math.sin(self._tick * sp.get("ear_speed", 0.1)) * sp.get("ear_wave", 1.5)
                self._model.SetParameterValue("Ear_SR1", ear_sway * 0.6)
                self._model.SetParameterValue("Ear_SL1", ear_sway * 0.6)
                self._model.SetParameterValue("ParamMouthOpenY", sp.get("mouth_open", 0.03))
                self._model.SetParameterValue("ParamMouthForm", sp.get("mouth_form", 0.15))
            except:
                pass

        self._live2d.clearBuffer(0.0, 0.0, 0.0, 0.0)
        self._model.Draw()

    def _on_tick(self):
        if not self._model:
            return

        self._tick += 0.12

        # 1. Animações procedurais básicas (Respiração, etc.)
        if self._current_state == KuriState.SLEEPING and hasattr(self, "_sleep_params"):
            sp = self._sleep_params
            breath = 0.5 + math.sin(self._tick * sp.get("breath_speed", 0.35)) * sp.get("breath_wave", 0.6) * 0.5
            self._model.SetParameterValue("ParamBreath", breath)

            self._model.SetParameterValue("ParamEyeLOpen", sp["ParamEyeLOpen"])
            self._model.SetParameterValue("ParamEyeROpen", sp["ParamEyeROpen"])
            if "ParamEyeLSmile" in sp:
                self._model.SetParameterValue("ParamEyeLSmile", sp.get("ParamEyeLSmile", 0.2))
                self._model.SetParameterValue("ParamEyeRSmile", sp.get("ParamEyeRSmile", 0.2))

            self._model.SetParameterValue("ParamAngleY", sp["ParamAngleY"])

            # Orelhas + boca relaxada sutis (usando parâmetros existentes)
            ear_sway = math.sin(self._tick * sp.get("ear_speed", 0.1)) * sp.get("ear_wave", 1.5)
            self._model.SetParameterValue("Ear_SR1", ear_sway * 0.6)
            self._model.SetParameterValue("Ear_SL1", ear_sway * 0.6)
            self._model.SetParameterValue("ParamMouthOpenY", sp.get("mouth_open", 0.03))
            self._model.SetParameterValue("ParamMouthForm", sp.get("mouth_form", 0.15))
            # desliga piscada normal no sono
        else:
            for param_id, cfg in self._procedural_params.items():
                base = float(cfg.get("base", 0.0))
                wave = float(cfg.get("wave", 0.0))
                speed = float(cfg.get("speed", 1.0))
                value = base + math.sin(self._tick * speed) * wave
                self._model.SetParameterValue(param_id, value)

        # 2. Sincronia labial ao falar (nível vem do TTS via bridge)
        if self._speaking:
            try:
                from gui.kuri_bridge import bridge
                level = bridge.mouth_open
            except Exception:
                level = 0.0
            if level > 0.02:
                mouth = 0.12 + level * 0.78
            else:
                mouth = 0.08 + (math.sin(self._tick * 8.0) + 1.0) * 0.08
            self._model.SetParameterValue("ParamMouthOpenY", mouth)

        # 3. Gesto de inclinação de cabeça ao falar
        speak_offset_z = 0.0
        if getattr(self, "_speak_gesture_tick", 0) > 0:
            self._speak_gesture_tick -= 1
            speak_offset_z = math.sin(self._speak_gesture_tick * 0.3) * 5.0
            self._model.SetParameterValue("ParamAngleZ", speak_offset_z)

        # 4. Olhar e movimentação seguindo o cursor do mouse (se ativado)
        target_angle_x = 0.0
        target_angle_y = 0.0
        target_eyeball_x = 0.0
        target_eyeball_y = 0.0
        
        if self.use_mouse_tracking and not self._deep_idle:
            try:
                cursor_pos = QCursor.pos()
                widget_center = self.mapToGlobal(self.rect().center())
                dx = cursor_pos.x() - widget_center.x()
                dy = cursor_pos.y() - widget_center.y()
                
                # Acorda do repouso se o mouse se mover significativamente
                if abs(dx - getattr(self, "_last_dx", 0.0)) > 5 or abs(dy - getattr(self, "_last_dy", 0.0)) > 5:
                    self._reset_activity()
                self._last_dx = dx
                self._last_dy = dy
                
                # Limita e converte em ângulos (-30 a 30) e olhar (-1 a 1)
                scale_factor = 250.0
                target_angle_x = _clamp((dx / scale_factor) * 30.0, -30.0, 30.0)
                target_angle_y = _clamp((-dy / scale_factor) * 30.0, -30.0, 30.0)
                target_eyeball_x = _clamp(dx / scale_factor, -1.0, 1.0)
                target_eyeball_y = _clamp(-dy / scale_factor, -1.0, 1.0)
            except Exception:
                pass

        # Lerp suave para os ângulos do mouse
        self._current_angle_x = _lerp(self._current_angle_x, target_angle_x, 0.15)
        self._current_angle_y = _lerp(self._current_angle_y, target_angle_y, 0.15)
        self._current_eyeball_x = _lerp(self._current_eyeball_x, target_eyeball_x, 0.15)
        self._current_eyeball_y = _lerp(self._current_eyeball_y, target_eyeball_y, 0.15)
        
        self._model.SetParameterValue("ParamAngleX", self._current_angle_x)
        self._model.SetParameterValue("ParamAngleY", self._current_angle_y)
        self._model.SetParameterValue("ParamEyeBallX", self._current_eyeball_x)
        self._model.SetParameterValue("ParamEyeBallY", self._current_eyeball_y)

        # 5. Controle de olhos + piscada (com suporte especial para sono)
        if self._current_state == KuriState.SLEEPING and hasattr(self, "_sleep_params"):
            sp = self._sleep_params
            try:
                self._model.StopAllMotions()
            except:
                pass
            self._model.SetParameterValue("ParamEyeLOpen", sp["ParamEyeLOpen"])
            self._model.SetParameterValue("ParamEyeROpen", sp["ParamEyeROpen"])
            if "ParamEyeLSmile" in sp:
                self._model.SetParameterValue("ParamEyeLSmile", sp.get("ParamEyeLSmile", 0.2))
                self._model.SetParameterValue("ParamEyeRSmile", sp.get("ParamEyeRSmile", 0.2))

            sway = math.sin(self._tick * 0.08) * 3.5
            self._model.SetParameterValue("ParamAngleY", sp["ParamAngleY"] + sway)

            breath = 0.5 + math.sin(self._tick * sp.get("breath_speed", 0.35)) * sp.get("breath_wave", 0.6) * 0.5
            try:
                self._model.SetParameterValue("ParamBreath", breath)
            except Exception:
                pass

            # Orelhas + boca relaxada (parâmetros que o artista já forneceu)
            ear_sway = math.sin(self._tick * sp.get("ear_speed", 0.1)) * sp.get("ear_wave", 1.5)
            self._model.SetParameterValue("Ear_SR1", ear_sway * 0.6)
            self._model.SetParameterValue("Ear_SL1", ear_sway * 0.6)
            self._model.SetParameterValue("ParamMouthOpenY", sp.get("mouth_open", 0.03))
            self._model.SetParameterValue("ParamMouthForm", sp.get("mouth_form", 0.15))

            try:
                self._model.StopAllMotions()
            except:
                pass
        else:
            # Piscada normal
            self._blink_tick += 1
            blink_interval = {
                "neutral": 120,
                "cool": 200,
                "surprised": 50,
                "blushing": 80,
                "angry": 240,
            }.get(self._current_emotion, 120)

            blink_frame = self._blink_tick % blink_interval
            eye_open = 1.0
            if blink_frame < 3:
                eye_open = 1.0 - (blink_frame + 1) * 0.33
            elif blink_frame < 6:
                eye_open = (blink_frame - 2) * 0.33

            eye_open = _clamp(eye_open, 0.0, 1.0)

            eye_base = {
                "angry": 0.65,
                "cool": 0.85,
            }.get(self._current_emotion, 1.0)

            final_eye_open = eye_open * eye_base

            # Wake up sequence
            if self._waking_up:
                self._wake_up_tick += 1
                if self._wake_up_tick < 15:
                    final_eye_open = 0.0
                elif self._wake_up_tick < 40:
                    final_eye_open = (self._wake_up_tick - 15) / 25.0
                else:
                    self._waking_up = False

            self._model.SetParameterValue("ParamEyeLOpen", final_eye_open)
            self._model.SetParameterValue("ParamEyeROpen", final_eye_open)

        self.update()

    def set_emotion(self, emotion: str):
        self._reset_activity()
        if emotion == self._current_emotion:
            return
        self._current_emotion = emotion
        self._refresh_expression()

    def set_speaking(self, speaking: bool):
        self._reset_activity()
        self._speaking = speaking
        if not speaking and self._model:
            self._model.SetParameterValue("ParamMouthOpenY", 0.0)
            # limpa os extras que usamos enquanto falava
            try:
                self._model.SetParameterValue("ParamMouthForm", 0.0)
                self._model.SetParameterValue("ParamEyeRSmile", 0.0)
                self._model.SetParameterValue("ParamEyeLSmile", 0.0)
            except:
                pass

    def set_state(self, state: KuriState):
        # ============================================================
        # SLEEP_ANIMATION_FIX (2026-06)
        # Problem: When entering SLEEPING (via mic suspension or 5min inactivity),
        # the sleeping visual (low eyes, head tilt, slow breath + ZZZ overlay) 
        # would flash for ~1s then immediately revert to normal "idle" motion.
        # Root cause: 
        #   - Normal "Idle" motion was still playing or blending over our manual params.
        #   - _reset_activity() was clearing _sleep_params and deep_idle on any activity.
        #   - State changes were not "sticky" for suspended mode.
        #   - Params set before model.Update() were being overridden.
        # Solution:
        #   - Special-case SLEEPING **before** any _reset_activity or normal apply.
        #   - Call StopAllMotions() aggressively on entry + every tick/paint.
        #   - Force sleepy params (eyes, angleY + sway, breath) **after** Update() in paintGL.
        #   - Guard _reset_activity() to do nothing if currently SLEEPING.
        #   - Re-force set_state(SLEEPING) periodically from kuri_core.py while _mic_suspended.
        #   - Always set_emotion("neutral") on sleep entry.
        # This makes the custom sleep pose + ZZZ persist while FPS is lowered by deep idle.
        # Search keywords: SLEEP_ANIMATION_FIX, SLEEP_VISUAL_PERSIST, LIVE2D_SLEEP
        # ============================================================
        if state == KuriState.SLEEPING:
            if self._current_state == state:
                return
            self._current_state = state
            self._enter_deep_idle()
            self._apply_sleep_visual()
            if self._model:
                try:
                    self._model.StopAllMotions()
                except Exception:
                    pass
            self._set_fps("idle")
            return

        self._reset_activity()
        if state == self._current_state:
            return
        self._current_state = state
        state_name = state.name.lower()
        self._set_fps(state_name)
        self._apply_state_animation(state_name)

    def _start_motion_group(self, group: str | None, *, random_idle: bool = False):
        if not self._model or not group:
            return
        try:
            groups = set(self._model.GetMotionGroups())
            if group not in groups:
                return
            if random_idle and group == "Idle":
                self._model.StartRandomMotion(group, priority=2)
            else:
                self._model.StartMotion(group, 0, priority=2)
        except Exception:
            pass

    def _apply_state_animation(self, state_name: str):
        if not self._model:
            return

        cfg = self._animation_map.get(state_name, {})
        self._procedural_params = cfg.get("procedural", {})
        self._state_expression = cfg.get("expression")

        motion_group = cfg.get("motion_group")
        if motion_group:
            self._start_motion_group(motion_group, random_idle=(state_name == "idle"))
        elif state_name == "idle":
            self._start_motion_group("Idle", random_idle=True)

        self._refresh_expression()

    def _apply_sleep_visual(self):
        """Aplica visual extra de sono no Live2D usando só os parâmetros que o artista já forneceu.
        Olhos quase fechados + leve smile relaxado + cabeça baixa + respiração lenta + orelhas e cabelo sutis."""
        if not self._model:
            return
        try:
            self._model.ResetExpressions()
            self._model.StopAllMotions()
        except:
            pass
        self._current_emotion = "neutral"

        self._sleep_params = {
            "ParamEyeLOpen": 0.05,
            "ParamEyeROpen": 0.05,
            "ParamEyeLSmile": 0.2,     # olhos mais "macios" fechados
            "ParamEyeRSmile": 0.2,
            "ParamAngleY": -14.0,
            "breath_speed": 0.18,
            "breath_wave": 1.1,
            # Orelhas bem devagar (parece que respira com as orelhas também)
            "ear_speed": 0.09,
            "ear_wave": 1.8,
            # Boquinha levemente relaxada
            "mouth_open": 0.03,
            "mouth_form": 0.15,
        }
        self._model.SetParameterValue("ParamEyeLOpen", self._sleep_params["ParamEyeLOpen"])
        self._model.SetParameterValue("ParamEyeROpen", self._sleep_params["ParamEyeROpen"])
        self._model.SetParameterValue("ParamAngleY", self._sleep_params["ParamAngleY"])

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_framing(self.height())

    def _resolve_expression_id(self) -> str | None:
        if self._state_expression and self._current_state == KuriState.ERROR:
            return self._state_expression
        return self._emotion_map.get(self._current_emotion)

    def _refresh_expression(self):
        if not self._model:
            return

        expression_id = self._resolve_expression_id()
        if expression_id:
            available = set(self._model.GetExpressionIds())
            if expression_id in available:
                self._model.ResetExpressions()
                self._model.SetExpression(expression_id)
        else:
            self._model.ResetExpressions()