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
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl, QTimer, QPoint, pyqtSignal, QObject

from gui.kuri_bridge import KuriState, bridge
from gui.settings_dialog import SettingsDialog, load_gui_config, save_gui_config
from gui.design_system import DesignTokens
from gui.animations import smooth_resize
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

        # Timers
        self._clock_timer = QTimer()
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)

        self._text_clear_timer = QTimer()
        self._text_clear_timer.setSingleShot(True)
        self._text_clear_timer.timeout.connect(self._hide_text_bubble)

        # Proxy
        self._signal_proxy = SignalProxy()
        self._signal_proxy.state_changed.connect(self._on_state_changed)
        self._signal_proxy.text_received.connect(self._on_text_received)
        self._signal_proxy.emotion_changed.connect(self._on_emotion_changed)

        bridge.on_state_change(lambda s: self._signal_proxy.state_changed.emit(s))
        bridge.on_text(lambda t: self._signal_proxy.text_received.emit(t))
        bridge.on_emotion(lambda e: self._signal_proxy.emotion_changed.emit(e))

        self._setup_ui()
        self._setup_player()
        self._restore_position()
        self._play_avatar("neutral")
        self._update_clock()

    def _setup_ui(self):
        self.setObjectName("kuri_root")
        self.setFixedSize(300, 420)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setStyleSheet(DesignTokens.get_main_style())

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(12, 12, 12, 12)
        self.root_layout.setSpacing(10)

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
        self.avatar_frame.setFixedSize(276, 276)
        self.avatar_frame.setStyleSheet(f"""
            QFrame#avatar_frame {{
                background-color: {DesignTokens.BG_CARD};
                border: 1px solid {DesignTokens.BORDER};
                border-radius: 138px;
            }}
        """)

        avatar_layout = QVBoxLayout(self.avatar_frame)
        avatar_layout.setContentsMargins(0, 0, 0, 0)

        self.video_widget = QVideoWidget()
        self.video_widget.setFixedSize(276, 276)
        # Hack para arredondar o vídeo no Qt: QVideoWidget não aceita border-radius via CSS bem.
        # Por enquanto vamos manter retangular mas dentro de um frame circular.
        avatar_layout.addWidget(self.video_widget)

        self.root_layout.addWidget(self.avatar_frame, 0, Qt.AlignmentFlag.AlignCenter)

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

    def _setup_player(self):
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

    def _update_clock(self):
        self.header_clock.setText(datetime.now().strftime("%H:%M"))

    def _on_state_changed(self, new_state: KuriState):
        self._current_state = new_state
        color = {
            KuriState.IDLE: DesignTokens.BORDER,
            KuriState.LISTENING: DesignTokens.COLOR_LISTENING,
            KuriState.THINKING: DesignTokens.COLOR_THINKING,
            KuriState.SPEAKING: DesignTokens.COLOR_SPEAKING,
            KuriState.ERROR: DesignTokens.COLOR_ERROR,
        }.get(new_state, DesignTokens.BORDER)

        self.indicator_bar.setStyleSheet(
            f"background-color: {color}; border-radius: 1px;"
        )

        if new_state == KuriState.LISTENING:
            self.btn_mic.setObjectName("btn_mic_active")
        else:
            self.btn_mic.setObjectName("")
        self.btn_mic.style().unpolish(self.btn_mic)
        self.btn_mic.style().polish(self.btn_mic)

    def _on_emotion_changed(self, emotion: str):
        self._play_avatar(emotion)

    def _on_text_received(self, text: str):
        self.text_bubble.setText(text)
        # Anima a expansão da bolha
        smooth_resize(self.text_bubble, 0, 60)
        self._text_clear_timer.start(8000)

    def _hide_text_bubble(self):
        smooth_resize(self.text_bubble, 60, 0)

    def _on_mic_clicked(self):
        if self._current_state == KuriState.LISTENING:
            bridge.send_command("stop_listen")
        else:
            bridge.send_command("start_listen")

    def _open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()
        self._config = load_gui_config()

    def _on_close_clicked(self):
        self._save_position()
        bridge.send_command("shutdown")
        QApplication.instance().quit()

    def mouseDoubleClickEvent(self, event):
        """Alterna entre modo normal e compacto."""
        if self._is_compact:
            self.setFixedSize(300, 420)
            self.avatar_frame.setFixedSize(276, 276)
            self.video_widget.setFixedSize(276, 276)
            self.header_title.show()
            self.header_clock.show()
            self._is_compact = False
        else:
            self.setFixedSize(100, 100)
            self.avatar_frame.setFixedSize(80, 80)
            self.video_widget.setFixedSize(80, 80)
            self.header_title.hide()
            self.header_clock.hide()
            self._is_compact = True

    # ── Posição e Drag (Mantidos) ──────────────────────────────────────────
    def _restore_position(self):
        pos = self._config.get("widget_pos")
        if pos and len(pos) == 2:
            self.move(pos[0], pos[1])
        else:
            screen = QApplication.primaryScreen().availableGeometry()
            self.move(
                screen.width() - self.width() - 20, screen.height() - self.height() - 20
            )

    def _save_position(self):
        self._config["widget_pos"] = [self.x(), self.y()]
        save_gui_config(self._config)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            self._save_position()

    def closeEvent(self, event):
        self._save_position()
        bridge.send_command("shutdown")
        event.accept()
