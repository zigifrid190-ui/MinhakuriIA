import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QApplication,
    QSizeGrip,
    QSystemTrayIcon,
    QMenu,
)
from PyQt6.QtGui import QIcon
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl, QTimer, QPoint, pyqtSignal, QObject, QRect

from gui.kuri_bridge import KuriState, bridge
from gui.settings_dialog import SettingsDialog, load_gui_config, save_gui_config
from gui.design_system import DesignTokens
from gui.animations import smooth_resize, fade_transition
from gui.live2d_avatar import Live2DAvatarWidget, can_use_live2d_avatar
from path_utils import get_resource_path

# ── Paths dos avatares ────────────────────────────────────────────────────────
_BASE = get_resource_path("InterfaceAva")
AVATAR_MAP = {
    "neutral": os.path.join(_BASE, "kuri_neutral_animated.mp4"),
    "cool": os.path.join(_BASE, "kuri_cool_animated.mp4"),
    "surprised": os.path.join(_BASE, "kuri_surprised_animated.mp4"),
    "blushing": os.path.join(_BASE, "kuri_blushing_animated.mp4"),
    "angry": os.path.join(_BASE, "kuri_angry_animated.mp4"),
}

MIN_WIDGET_SIZE = (88, 88)
DEFAULT_WIDGET_SIZE = (380, 380)
MAX_WIDGET_SIZE = (420, 520)
COMPACT_WIDGET_SIZE = (88, 88)
MINI_MODE_THRESHOLD = 208
MINI_MARGIN = 6
NORMAL_MARGIN = 10


class SignalProxy(QObject):
    state_changed = pyqtSignal(object)
    text_received = pyqtSignal(str)
    emotion_changed = pyqtSignal(str)


class KuriWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._config = load_gui_config()
        self._drag_pos: QPoint | None = None
        self._current_state = KuriState.IDLE
        self._is_compact = False
        self._expanded_size = self._load_widget_size()
        self._use_live2d = self._config.get("use_live2d_avatar", True) and can_use_live2d_avatar()
        self._live2d_widget: Live2DAvatarWidget | None = None

        # Timers
        self._clock_timer = QTimer()
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)

        self._text_clear_timer = QTimer()
        self._text_clear_timer.setSingleShot(True)
        self._text_clear_timer.timeout.connect(self._hide_text_bubble)

        self._resize_save_timer = QTimer()
        self._resize_save_timer.setSingleShot(True)
        self._resize_save_timer.timeout.connect(self._save_position)

        self._emotion_reset_timer = QTimer()
        self._emotion_reset_timer.setSingleShot(True)
        self._emotion_reset_timer.timeout.connect(self._reset_emotion_to_neutral)

        # Proxy
        self._signal_proxy = SignalProxy()
        self._signal_proxy.state_changed.connect(self._on_state_changed)
        self._signal_proxy.text_received.connect(self._on_text_received)
        self._signal_proxy.emotion_changed.connect(self._on_emotion_changed)

        bridge.on_state_change(lambda s: self._signal_proxy.state_changed.emit(s))
        bridge.on_text(lambda t: self._signal_proxy.text_received.emit(t))
        bridge.on_emotion(lambda e: self._signal_proxy.emotion_changed.emit(e))

        self._setup_ui()
        if self._live2d_widget:
            self._live2d_widget.use_mouse_tracking = self._config.get("use_mouse_tracking", True)
        self._setup_tray()
        if not self._use_live2d:
            self._setup_player()
        self._restore_position()
        self._set_avatar_emotion("neutral")
        self._update_clock()

    def _load_widget_size(self) -> tuple[int, int]:
        saved = self._config.get("widget_size")
        if saved and len(saved) == 2:
            width = max(MIN_WIDGET_SIZE[0], min(int(saved[0]), MAX_WIDGET_SIZE[0]))
            height = max(MIN_WIDGET_SIZE[1], min(int(saved[1]), MAX_WIDGET_SIZE[1]))
            return width, height
        return DEFAULT_WIDGET_SIZE

    def _setup_ui(self):
        self.setObjectName("kuri_root")
        self.setMinimumSize(*MIN_WIDGET_SIZE)
        self.setMaximumSize(*MAX_WIDGET_SIZE)
        self.resize(*self._expanded_size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setStyleSheet(DesignTokens.get_main_style())

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(NORMAL_MARGIN, NORMAL_MARGIN, NORMAL_MARGIN, NORMAL_MARGIN)
        self.root_layout.setSpacing(8)

        # ── Header ────────────────────────────────────────────────────────
        header = QHBoxLayout()
        self.header_title = QLabel("KURI // PERSONAL AI")
        self.header_title.setObjectName("header_title")

        self.header_clock = QLabel("00:00")
        self.header_clock.setObjectName("header_clock")

        header.addWidget(self.header_title)
        header.addStretch()
        header.addWidget(self.header_clock)
        self.root_layout.addLayout(header)

        # ── Avatar Container ─────────────────────────────────────────────
        self.avatar_frame = QFrame()
        self.avatar_frame.setObjectName("avatar_frame")
        self.avatar_frame.setFixedSize(120, 120)
        self._update_avatar_frame_style(120)

        avatar_layout = QVBoxLayout(self.avatar_frame)
        avatar_layout.setContentsMargins(0, 0, 0, 0)

        if self._use_live2d:
            self._live2d_widget = Live2DAvatarWidget(self.avatar_frame)
            self._live2d_widget.setFixedSize(120, 120)
            avatar_layout.addWidget(self._live2d_widget)
            self.video_widget = None
        else:
            self.video_widget = QVideoWidget()
            self.video_widget.setFixedSize(120, 120)
            # Hack para arredondar o vídeo no Qt: QVideoWidget não aceita border-radius via CSS bem.
            # Por enquanto vamos manter retangular mas dentro de um frame circular.
            avatar_layout.addWidget(self.video_widget)

        self.root_layout.addWidget(self.avatar_frame, 0, Qt.AlignmentFlag.AlignCenter)

        # ── Indicador de Sono (Zzz overlay) ──────────────────────────────
        # See docs/SLEEP_MODE_FIX.md for why we re-force SLEEPING state
        # and tie visibility strictly to KuriState.SLEEPING.
        self.sleep_indicator = QLabel("Zzz")
        self.sleep_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sleep_indicator.setStyleSheet("""
            font-size: 12px; 
            color: #9aa0c8; 
            background: rgba(18,18,38,175);
            border-radius: 4px;
            padding: 0px 3px;
            font-weight: bold;
            letter-spacing: 0.5px;
        """)
        self.sleep_indicator.setFixedSize(28, 15)
        self.sleep_indicator.hide()
        # Zzz posicionado bem próximo do topo da cabeça da Kuri (ajustado empiricamente para o framing do Live2D)
        self.sleep_indicator.setParent(self.avatar_frame)
        self.sleep_indicator.move(50, -11)  # mais próximo da cabeça (acima do topo do modelo)

        # Simple Zzz animation timer
        self._zzz_timer = QTimer(self)
        self._zzz_timer.timeout.connect(self._animate_zzz)
        self._zzz_index = 0
        self._zzz_strings = ["Zzz", "zZz", "ZzZ", "zzZ", "Z z z"]

        # ── Indicador de Estado ──────────────────────────────────────────
        self.indicator_bar = QFrame()
        self.indicator_bar.setFixedHeight(2)
        self.indicator_bar.setStyleSheet(
            f"background-color: {DesignTokens.BORDER}; border-radius: 1px;"
        )
        self.root_layout.addWidget(self.indicator_bar)

        # ── Bolha de Texto (Expansível) ──────────────────────────────────
        self.text_bubble = QLabel("")
        self.text_bubble.setObjectName("text_bubble")
        self.text_bubble.setWordWrap(True)
        self.text_bubble.setMinimumHeight(0)
        self.text_bubble.setMaximumHeight(0)
        self.text_bubble.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self.root_layout.addWidget(self.text_bubble)

        # ── Bottom Bar ───────────────────────────────────────────────────
        bottom_bar = QHBoxLayout()

        self.btn_mic = QPushButton("🎤")
        self.btn_mic.setProperty("class", "btn_icon")
        self.btn_mic.setFixedSize(40, 36)
        self.btn_mic.clicked.connect(self._on_mic_clicked)

        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setProperty("class", "btn_icon")
        self.btn_settings.setFixedSize(36, 36)
        self.btn_settings.clicked.connect(self._open_settings)

        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("btn_close")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setStyleSheet("color: #444; border: none; font-size: 14px;")
        self.btn_close.clicked.connect(self._on_close_clicked)

        bottom_bar.addWidget(self.btn_mic)
        bottom_bar.addWidget(self.btn_settings)
        bottom_bar.addStretch()
        bottom_bar.addWidget(self.btn_close)

        self.root_layout.addLayout(bottom_bar)

        self._size_grip = QSizeGrip(self)
        self._size_grip.setFixedSize(14, 14)
        self._size_grip.setStyleSheet("background: transparent;")

        self.status_dot = QLabel(self)
        self.status_dot.setObjectName("status_dot")
        self.status_dot.setFixedSize(12, 12)
        self.status_dot.setVisible(False)

        self._sync_avatar_layout()

    def _chrome_height(self) -> int:
        if self._is_compact:
            return 24
        chrome = self.root_layout.contentsMargins().top() + self.root_layout.contentsMargins().bottom()
        chrome += self.root_layout.spacing() * 4
        chrome += self.indicator_bar.height()
        chrome += self.btn_mic.height()
        if self.text_bubble.maximumHeight() > 0:
            chrome += self.text_bubble.maximumHeight()
        if not self.header_title.isHidden():
            chrome += self.header_title.sizeHint().height()
        return chrome

    def _update_avatar_frame_style(self, avatar_size: int):
        radius = max(8, avatar_size // 10)
        self.avatar_frame.setStyleSheet(f"""
            QFrame#avatar_frame {{
                background-color: {DesignTokens.BG_CARD};
                border: 1px solid {DesignTokens.BORDER};
                border-radius: {radius}px;
            }}
        """)

    def _sync_avatar_layout(self):
        mini_mode = (
            self._is_compact
            or self.width() < MINI_MODE_THRESHOLD
            or self.height() < MINI_MODE_THRESHOLD
        )
        self._set_compact_ui_visible(not mini_mode)

        margin = MINI_MARGIN if mini_mode else NORMAL_MARGIN
        self.root_layout.setContentsMargins(margin, margin, margin, margin)

        margins = self.root_layout.contentsMargins()
        available_w = self.width() - margins.left() - margins.right()
        available_h = self.height() - margins.top() - margins.bottom() - self._chrome_height()
        avatar_size = max(72, min(available_w, available_h))

        self._update_avatar_frame_style(avatar_size)
        self.avatar_frame.setFixedSize(avatar_size, avatar_size)

        if self._live2d_widget:
            self._live2d_widget.setFixedSize(avatar_size, avatar_size)
            self._live2d_widget.update_framing(avatar_size)
        elif self.video_widget:
            self.video_widget.setFixedSize(avatar_size, avatar_size)

        if mini_mode and hasattr(self, "status_dot"):
            # Move para o canto inferior direito do frame do avatar
            self.status_dot.move(
                self.avatar_frame.x() + avatar_size - 10,
                self.avatar_frame.y() + avatar_size - 10
            )
            self.status_dot.setVisible(True)
            self.status_dot.raise_()
        elif hasattr(self, "status_dot"):
            self.status_dot.setVisible(False)

        self._size_grip.move(self.width() - self._size_grip.width() - 4, self.height() - self._size_grip.height() - 4)
        self._size_grip.raise_()

    def _setup_player(self):
        if not self.video_widget:
            return
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)
        self.audio_output.setVolume(0.0)
        self.player.setLoops(-1)

    def _play_avatar(self, emotion: str):
        path = AVATAR_MAP.get(emotion, AVATAR_MAP["neutral"])
        if not path or not os.path.exists(path):
            return
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
        self.player.play()

    def _set_avatar_emotion(self, emotion: str):
        if self._live2d_widget:
            self._live2d_widget.set_emotion(emotion)
        elif hasattr(self, "player"):
            self._play_avatar(emotion)

    def _update_clock(self):
        self.header_clock.setText(datetime.now().strftime("%H:%M"))

    def _animate_zzz(self):
        if hasattr(self, 'sleep_indicator') and self.sleep_indicator.isVisible():
            self._zzz_index = (self._zzz_index + 1) % len(self._zzz_strings)
            self.sleep_indicator.setText(self._zzz_strings[self._zzz_index])
            
            # Animação flutuante mais próxima da cabeça: bob maior e suave
            base_y = -11
            offset = 2 if (self._zzz_index % 2 == 0) else -2
            self.sleep_indicator.move(50, base_y + offset)

    def _on_state_changed(self, new_state: KuriState):
        self._current_state = new_state
        color = {
            KuriState.IDLE: DesignTokens.BORDER,
            KuriState.LISTENING: DesignTokens.COLOR_LISTENING,
            KuriState.THINKING: DesignTokens.COLOR_THINKING,
            KuriState.SPEAKING: DesignTokens.COLOR_SPEAKING,
            KuriState.SLEEPING: DesignTokens.COLOR_SLEEPING,
            KuriState.ERROR: DesignTokens.COLOR_ERROR,
        }.get(new_state, DesignTokens.BORDER)

        self.indicator_bar.setStyleSheet(
            f"background-color: {color}; border-radius: 2px;"
        )
        self.indicator_bar.setFixedHeight(4)

        if new_state == KuriState.LISTENING:
            self.btn_mic.setObjectName("btn_mic_active")
        else:
            self.btn_mic.setObjectName("")
        self.btn_mic.style().unpolish(self.btn_mic)
        self.btn_mic.style().polish(self.btn_mic)

        # Atualiza a cor do status dot em modo compacto
        if hasattr(self, "status_dot") and self.status_dot:
            self.status_dot.setStyleSheet(
                f"background-color: {color}; border: 1.5px solid {DesignTokens.BG_ROOT}; border-radius: 6px;"
            )

        # Atualiza o glow animado ao redor do avatar_frame
        self._update_glow(color, new_state)

        if self._live2d_widget:
            self._live2d_widget.set_state(new_state)
            self._live2d_widget.set_speaking(new_state == KuriState.SPEAKING)
            if new_state == KuriState.SLEEPING:
                # Força deep idle visual para sono
                try:
                    self._live2d_widget._enter_deep_idle()
                except Exception:
                    pass
            # Show Zzz indicator only in sleep
            if hasattr(self, 'sleep_indicator'):
                if new_state == KuriState.SLEEPING:
                    self.sleep_indicator.show()
                    if hasattr(self, '_zzz_timer'):
                        self._zzz_timer.start(900)  # slow gentle cycle
                    # Dim the avatar a bit for nice sleepy atmosphere
                    self.avatar_frame.setStyleSheet(f"""
                        QFrame#avatar_frame {{
                            background-color: {DesignTokens.BG_CARD};
                            border: 1px solid {DesignTokens.COLOR_SLEEPING};
                            border-radius: {radius}px;
                            opacity: 0.75;
                        }}
                    """)
                else:
                    self.sleep_indicator.hide()
                    if hasattr(self, '_zzz_timer'):
                        self._zzz_timer.stop()
                    # Restore normal style
                    self._update_avatar_frame_style(self.avatar_frame.width())

    def _update_glow(self, color_hex, state):
        """Atualiza a borda colorida ao redor do frame do avatar.
        
        NOTA: Evitamos QGraphicsDropShadowEffect no avatar_frame pois ele contém
        um QOpenGLWidget (Live2D). Efeitos gráficos em pais de OpenGL widgets causam
        composição offscreen → fundo transparente + queda de FPS.
        Em vez disso, usamos uma borda CSS estilizada com transição de cor.
        """
        if hasattr(self, "_glow_anim") and self._glow_anim:
            try:
                self._glow_anim.stop()
            except Exception:
                pass
            self._glow_anim = None

        avatar_size = self.avatar_frame.width()
        radius = max(8, avatar_size // 10)

        if state in (KuriState.IDLE, KuriState.SLEEPING):
            border_color = DesignTokens.COLOR_SLEEPING if state == KuriState.SLEEPING else DesignTokens.BORDER
            self.avatar_frame.setStyleSheet(f"""
                QFrame#avatar_frame {{
                    background-color: {DesignTokens.BG_CARD};
                    border: 1px solid {border_color};
                    border-radius: {radius}px;
                }}
            """)
            return

        # Borda colorida sólida — zero overhead de composição
        self.avatar_frame.setStyleSheet(f"""
            QFrame#avatar_frame {{
                background-color: {DesignTokens.BG_CARD};
                border: 2px solid {color_hex};
                border-radius: {radius}px;
            }}
        """)

    def _on_emotion_changed(self, emotion: str):
        if self._use_live2d:
            # No Live2D a transição de expressões é nativa e suave. 
            # Evitamos QGraphicsOpacityEffect no OpenGLWidget para prevenir perda de contexto e tela preta.
            self._set_avatar_emotion(emotion)
        else:
            def change_func():
                self._set_avatar_emotion(emotion)
            # Suaviza a transição de emoção com fade out/in do frame do avatar (apenas para MP4)
            fade_transition(self.avatar_frame, change_func, duration=240)
        
        # Se for diferente de neutral, inicia ou reseta timer de 2 min, senão desativa
        if emotion != "neutral":
            self._emotion_reset_timer.start(120000)  # 2 minutos (120000ms)
        else:
            self._emotion_reset_timer.stop()

    def _reset_emotion_to_neutral(self):
        self._on_emotion_changed("neutral")

    def _on_text_received(self, text: str):
        # Para animação anterior se houver
        if hasattr(self, "_typewriter_timer") and self._typewriter_timer:
            try:
                self._typewriter_timer.stop()
            except Exception:
                pass

        config = load_gui_config()
        use_typewriter = config.get("use_typewriter", True)

        if not use_typewriter:
            self.text_bubble.setText(text)
            smooth_resize(self.text_bubble, 0, 60)
            self._text_clear_timer.start(8000)
            return

        self._typewriter_full_text = text
        self._typewriter_idx = 0
        self.text_bubble.setText("")
        smooth_resize(self.text_bubble, 0, 60)

        # Dispara balanço de cabeça (micro-expressão de fala) se Live2D ativo
        if self._live2d_widget:
            try:
                self._live2d_widget.trigger_speak_gesture()
            except Exception:
                pass

        self._typewriter_timer = QTimer(self)
        self._typewriter_timer.timeout.connect(self._tick_typewriter)
        self._typewriter_timer.start(18)  # 18ms por caractere

    def _tick_typewriter(self):
        self._typewriter_idx += 1
        self.text_bubble.setText(self._typewriter_full_text[:self._typewriter_idx])
        if self._typewriter_idx >= len(self._typewriter_full_text):
            self._typewriter_timer.stop()
            self._text_clear_timer.start(8000)

    def _hide_text_bubble(self):
        # Para animação de typewriter se o balão sumir antes de terminar
        if hasattr(self, "_typewriter_timer") and self._typewriter_timer:
            try:
                self._typewriter_timer.stop()
            except Exception:
                pass
        smooth_resize(self.text_bubble, 60, 0)

    def _setup_tray(self):
        """Inicializa o ícone da bandeja do sistema e o menu de contexto."""
        self.tray_icon = QSystemTrayIcon(self)
        icon_path = get_resource_path("kuri.ico")
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        self.tray_icon.setToolTip("KURI — Personal AI")

        # Menu do Tray
        tray_menu = QMenu()

        show_action = tray_menu.addAction("Exibir Kuri")
        show_action.triggered.connect(self._restore_window)

        mic_action = tray_menu.addAction("Silenciar / Ativar Mic")
        mic_action.triggered.connect(self._on_mic_clicked)

        settings_action = tray_menu.addAction("Configurações")
        settings_action.triggered.connect(self._open_settings)

        tray_menu.addSeparator()

        quit_action = tray_menu.addAction("Sair")
        quit_action.triggered.connect(self._quit_app)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_icon_activated)
        self.tray_icon.show()

    def _restore_window(self):
        """Exibe e foca a janela da Kuri.
        
        NOTA: Não usamos QGraphicsOpacityEffect aqui pois a janela raiz contém
        um QOpenGLWidget (Live2D). Aplicar efeitos de opacidade na hierarquia
        do OpenGL causa composição offscreen → transparência intermitente.
        """
        self.show()
        self.activateWindow()
        self.raise_()

    def _on_tray_icon_activated(self, reason):
        """Trata o clique no ícone da bandeja."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:  # Clique simples
            if self.isVisible():
                self.hide()
            else:
                self._restore_window()

    def _quit_app(self):
        """Encerra a aplicação por completo."""
        self._save_position()
        bridge.send_command("shutdown")
        QApplication.instance().quit()

    def _on_mic_clicked(self):
        if self._current_state == KuriState.LISTENING:
            bridge.send_command("stop_listen")
        else:
            bridge.send_command("start_listen")

    def _open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()
        self._config = load_gui_config()
        if self._live2d_widget:
            self._live2d_widget.use_mouse_tracking = self._config.get("use_mouse_tracking", True)

    def _on_close_clicked(self):
        """Minimiza para a bandeja ao fechar pelo botão da GUI."""
        self._save_position()
        self.hide()
        self.tray_icon.showMessage(
            "KURI",
            "Kuri continua ativa em segundo plano.",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

    def mouseDoubleClickEvent(self, event):
        """Alterna entre modo compacto (quadrado mínimo) e último tamanho expandido."""
        if self._is_compact:
            self._is_compact = False
            self.resize(*self._expanded_size)
            self.header_title.show()
            self.header_clock.show()
        else:
            self._expanded_size = (self.width(), self.height())
            self._is_compact = True
            self.resize(*COMPACT_WIDGET_SIZE)
            self.header_title.hide()
            self.header_clock.hide()
        self._sync_avatar_layout()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._is_compact:
            self._expanded_size = (self.width(), self.height())
        self._sync_avatar_layout()
        self._resize_save_timer.start(400)

    def _set_compact_ui_visible(self, visible: bool):
        self.header_title.setVisible(visible)
        self.header_clock.setVisible(visible)
        self.indicator_bar.setVisible(visible)
        self.text_bubble.setVisible(visible)
        self.btn_mic.setVisible(visible)
        self.btn_settings.setVisible(visible)
        self.btn_close.setVisible(visible)

    # ── Posição e Drag (Mantidos) ──────────────────────────────────────────
    def _restore_position(self):
        pos = self._config.get("widget_pos")
        if pos and len(pos) == 2:
            x, y = pos[0], pos[1]
            visible = False
            for screen in QApplication.screens():
                geom = screen.availableGeometry()
                window_rect = QRect(x, y, self.width(), self.height())
                if geom.intersects(window_rect):
                    visible = True
                    break
            if visible:
                self.move(x, y)
                return
        
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.width() - self.width() - 20, screen.height() - self.height() - 20
        )

    def _save_position(self):
        x = self.x()
        y = self.y()
        screen = self.screen()
        if not screen:
            screen = QApplication.primaryScreen()
        geom = screen.availableGeometry()
        
        # Clamp bounds
        x = max(geom.left(), min(x, geom.right() - self.width()))
        y = max(geom.top(), min(y, geom.bottom() - self.height()))
        
        self._config["widget_pos"] = [x, y]
        if not self._is_compact:
            self._config["widget_size"] = [self.width(), self.height()]
        save_gui_config(self._config)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            self._save_position()
            event.accept()

    def closeEvent(self, event):
        self._save_position()
        bridge.send_command("shutdown")
        event.accept()
