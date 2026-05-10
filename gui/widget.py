"""
widget.py — Janela principal do widget da Kuri.

Design: GAMER HUD MINIMALISTA
- 260x320px, sem borda, always-on-top, arrastável
- Avatar MP4 em loop via QMediaPlayer
- Indicadores de estado com cor e animação
- Botões: 🎤 Falar | ⚙ Config | ✕ Fechar
"""

import os
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSizePolicy, QApplication
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import (
    Qt, QUrl, QTimer, QPoint, QPropertyAnimation,
    QEasingCurve, pyqtSignal, QObject
)
from PyQt6.QtGui import QFont, QColor, QPalette, QCursor

from gui.kuri_bridge import KuriState, bridge
from gui.settings_dialog import SettingsDialog, load_gui_config, save_gui_config
from path_utils import get_resource_path

# ── Paths dos avatares ────────────────────────────────────────────────────────

# Caminho para os vídeos de avatar
_BASE = get_resource_path("InterfaceAva")

AVATAR_MAP = {
    "neutral":   os.path.join(_BASE, "kuri_neutral_animated.mp4"),
    "cool":      os.path.join(_BASE, "kuri_cool_animated.mp4"),
    "surprised": os.path.join(_BASE, "kuri_surprised_animated.mp4"),
    "blushing":  os.path.join(_BASE, "kuri_blushing_animated.mp4"),
    "angry":     os.path.join(_BASE, "kuri_angry_animated.mp4"),
}

# ── Cores por estado ──────────────────────────────────────────────────────────
STATE_COLORS = {
    KuriState.IDLE:      "#3A3A3A",   # cinza dim
    KuriState.LISTENING: "#00FF88",   # verde neon
    KuriState.THINKING:  "#FFB800",   # âmbar
    KuriState.SPEAKING:  "#00BFFF",   # azul gelo
    KuriState.ERROR:     "#FF3333",   # vermelho
}

STATE_LABELS = {
    KuriState.IDLE:      "AGUARDANDO",
    KuriState.LISTENING: "OUVINDO...",
    KuriState.THINKING:  "PENSANDO...",
    KuriState.SPEAKING:  "FALANDO...",
    KuriState.ERROR:     "ERRO",
}

# ── Stylesheet principal ──────────────────────────────────────────────────────
WIDGET_STYLE = """
QWidget#kuri_root {
    background-color: #0D0D0D;
    border: 1px solid #1E1E1E;
}
QLabel#state_label {
    color: #00FF88;
    font-family: 'JetBrains Mono', 'Consolas', 'Courier New', monospace;
    font-size: 10px;
    letter-spacing: 3px;
    padding: 0 4px;
}
QLabel#text_bubble {
    color: #C0C0C0;
    font-family: 'JetBrains Mono', 'Consolas', 'Courier New', monospace;
    font-size: 10px;
    padding: 4px 8px;
    background-color: #111111;
    border-left: 2px solid #1E1E1E;
}
QFrame#indicator_bar {
    border-radius: 0px;
    max-height: 3px;
    min-height: 3px;
}
QFrame#bottom_bar {
    background-color: #111111;
    border-top: 1px solid #1E1E1E;
    max-height: 44px;
    min-height: 44px;
}
QPushButton#btn_mic {
    background-color: transparent;
    color: #00FF88;
    border: 1px solid #00FF88;
    border-radius: 0px;
    font-size: 16px;
    min-width: 38px;
    max-width: 38px;
    min-height: 32px;
    max-height: 32px;
}
QPushButton#btn_mic:hover {
    background-color: #001F0F;
}
QPushButton#btn_mic:pressed {
    background-color: #003318;
}
QPushButton#btn_settings {
    background-color: transparent;
    color: #606060;
    border: 1px solid #2A2A2A;
    border-radius: 0px;
    font-size: 14px;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
}
QPushButton#btn_settings:hover {
    color: #E0E0E0;
    border-color: #505050;
}
QPushButton#btn_close {
    background-color: transparent;
    color: #444444;
    border: none;
    border-radius: 0px;
    font-size: 14px;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
}
QPushButton#btn_close:hover {
    color: #FF3333;
}
"""


class SignalProxy(QObject):
    """Proxy para emitir sinais do PyQt a partir de threads externas."""
    state_changed = pyqtSignal(object)
    text_received = pyqtSignal(str)
    emotion_changed = pyqtSignal(str)


class KuriWidget(QWidget):
    """Widget flutuante principal da Kuri."""

    def __init__(self):
        super().__init__()
        self._config = load_gui_config()
        self._drag_pos: QPoint | None = None
        self._current_state = KuriState.IDLE
        self._text_clear_timer = QTimer()
        self._text_clear_timer.setSingleShot(True)
        self._text_clear_timer.timeout.connect(self._clear_text_bubble)

        # Proxy para receber sinais de threads externas com segurança
        self._signal_proxy = SignalProxy()
        self._signal_proxy.state_changed.connect(self._on_state_changed)
        self._signal_proxy.text_received.connect(self._on_text_received)
        self._signal_proxy.emotion_changed.connect(self._on_emotion_changed)

        # Registra callbacks no bridge
        bridge.on_state_change(lambda s: self._signal_proxy.state_changed.emit(s))
        bridge.on_text(lambda t: self._signal_proxy.text_received.emit(t))
        bridge.on_emotion(lambda e: self._signal_proxy.emotion_changed.emit(e))

        self._setup_ui()
        self._setup_player()
        self._restore_position()
        self._play_avatar("neutral")

    # ── Setup UI ──────────────────────────────────────────────────────────────

    def _setup_ui(self):
        self.setObjectName("kuri_root")
        self.setFixedSize(260, 320)
        self.setStyleSheet(WIDGET_STYLE)
        self.setWindowTitle("Kuri")

        # Flags: sem borda, always-on-top, aparece na barra de tarefas
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Área do vídeo ─────────────────────────────────────────────────
        self.video_widget = QVideoWidget()
        self.video_widget.setFixedHeight(240)
        self.video_widget.setStyleSheet("background-color: #0D0D0D;")
        root_layout.addWidget(self.video_widget)

        # ── Barra de indicador de estado (3px colorida) ───────────────────
        self.indicator_bar = QFrame()
        self.indicator_bar.setObjectName("indicator_bar")
        self.indicator_bar.setStyleSheet(
            "QFrame { background-color: #3A3A3A; max-height: 3px; min-height: 3px; }"
        )
        root_layout.addWidget(self.indicator_bar)

        # ── Label de estado ───────────────────────────────────────────────
        state_row = QHBoxLayout()
        state_row.setContentsMargins(8, 4, 8, 0)

        self.state_label = QLabel("AGUARDANDO")
        self.state_label.setObjectName("state_label")
        state_row.addWidget(self.state_label)
        state_row.addStretch()
        root_layout.addLayout(state_row)

        # ── Bolha de texto ────────────────────────────────────────────────
        self.text_bubble = QLabel("")
        self.text_bubble.setObjectName("text_bubble")
        self.text_bubble.setWordWrap(True)
        self.text_bubble.setFixedHeight(30)
        self.text_bubble.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        root_layout.addWidget(self.text_bubble)

        # ── Bottom bar com botões ─────────────────────────────────────────
        bottom_bar = QFrame()
        bottom_bar.setObjectName("bottom_bar")
        btn_layout = QHBoxLayout(bottom_bar)
        btn_layout.setContentsMargins(10, 6, 10, 6)
        btn_layout.setSpacing(8)

        self.btn_mic = QPushButton("🎤")
        self.btn_mic.setObjectName("btn_mic")
        self.btn_mic.setToolTip("Ativar / Desativar escuta")
        self.btn_mic.clicked.connect(self._on_mic_clicked)

        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setObjectName("btn_settings")
        self.btn_settings.setToolTip("Configurações de áudio")
        self.btn_settings.clicked.connect(self._open_settings)

        spacer = QFrame()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("btn_close")
        self.btn_close.setToolTip("Fechar Kuri")
        self.btn_close.clicked.connect(self._on_close_clicked)

        btn_layout.addWidget(self.btn_mic)
        btn_layout.addWidget(self.btn_settings)
        btn_layout.addWidget(spacer)
        btn_layout.addWidget(self.btn_close)

        root_layout.addWidget(bottom_bar)

    def _setup_player(self):
        """Configura QMediaPlayer para loop do avatar."""
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)
        self.audio_output.setVolume(0.0)  # Avatar é mudo; áudio da Kuri é via pygame

        # Loop infinito nativo do Qt6 para evitar tela preta
        self.player.setLoops(-1)

    # ── Player ────────────────────────────────────────────────────────────────

    def _play_avatar(self, emotion: str):
        """Troca e inicia loop do vídeo correspondente à emoção."""
        path = AVATAR_MAP.get(emotion, AVATAR_MAP["neutral"])
        if not path or not os.path.exists(path):
            return
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
        self.player.play()

    # ── Handlers de Estado ────────────────────────────────────────────────────

    def _on_state_changed(self, new_state: KuriState):
        """Atualiza visuais quando o estado da Kuri muda."""
        self._current_state = new_state
        color = STATE_COLORS.get(new_state, "#3A3A3A")
        label = STATE_LABELS.get(new_state, "")

        # Barra de indicador
        self.indicator_bar.setStyleSheet(
            f"QFrame {{ background-color: {color}; max-height: 3px; min-height: 3px; }}"
        )
        # Label de estado
        self.state_label.setStyleSheet(
            f"QLabel {{ color: {color}; font-family: 'Consolas', monospace; "
            f"font-size: 10px; letter-spacing: 3px; padding: 0 4px; }}"
        )
        self.state_label.setText(label)

        # Botão de mic muda visual no estado LISTENING
        if new_state == KuriState.LISTENING:
            self.btn_mic.setStyleSheet(
                "QPushButton { background-color: #003318; color: #00FF88; "
                "border: 1px solid #00FF88; font-size: 16px; "
                "min-width: 38px; max-width: 38px; min-height: 32px; max-height: 32px; }"
            )
        else:
            self.btn_mic.setStyleSheet("")  # Volta ao stylesheet global

    def _on_emotion_changed(self, emotion: str):
        """Atualiza a animação do avatar."""
        self._play_avatar(emotion)

    def _on_text_received(self, text: str):
        """Exibe o texto da Kuri na bolha (truncado em 60 chars) por 6 segundos."""
        truncated = text[:60] + ("..." if len(text) > 60 else "")
        self.text_bubble.setText(truncated)
        self._text_clear_timer.start(6000)

    def _clear_text_bubble(self):
        self.text_bubble.setText("")

    # ── Ações dos botões ─────────────────────────────────────────────────────

    def _on_mic_clicked(self):
        """Envia comando toggle para o core."""
        if self._current_state == KuriState.LISTENING:
            bridge.send_command("stop_listen")
        else:
            bridge.send_command("start_listen")

    def _open_settings(self):
        """Abre o painel de configurações de áudio."""
        dlg = SettingsDialog(self)
        if dlg.exec():
            # Recarrega config após salvar
            self._config = load_gui_config()

    def _on_close_clicked(self):
        """Salva posição e fecha gracefully."""
        self._save_position()
        bridge.send_command("shutdown")
        QApplication.instance().quit()

    # ── Posição ───────────────────────────────────────────────────────────────

    def _restore_position(self):
        """Restaura a última posição salva; padrão: canto inferior direito."""
        pos = self._config.get("widget_pos")
        if pos and isinstance(pos, list) and len(pos) == 2:
            self.move(pos[0], pos[1])
        else:
            # Padrão: canto inferior direito
            screen = QApplication.primaryScreen().availableGeometry()
            self.move(
                screen.width() - self.width() - 20,
                screen.height() - self.height() - 20
            )

    def _save_position(self):
        """Salva posição atual no config."""
        self._config["widget_pos"] = [self.x(), self.y()]
        save_gui_config(self._config)

    # ── Arrastar ──────────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            self._save_position()

    # ── Fechar com X da barra de tarefas ─────────────────────────────────────

    def closeEvent(self, event):
        self._save_position()
        bridge.send_command("shutdown")
        event.accept()
