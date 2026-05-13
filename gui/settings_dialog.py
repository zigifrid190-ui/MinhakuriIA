"""
settings_dialog.py — Painel de configuração de dispositivos de áudio da Kuri.

Design: HUD Minimalista
- Fundo quase preto #0D0D0D
- Acento verde neon #00FF88
- Bordas sharp (0px radius)
- Tipografia monospace
"""

import json
import os
import sounddevice as sd
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QSlider, QPushButton, QFrame,
    QCheckBox, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from config import USE_PREMIUM_TTS

GUI_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "kuri_gui_config.json")


def load_gui_config() -> dict:
    """Carrega configurações da GUI salvas em disco."""
    defaults = {
        "input_device": None,
        "output_device": None,
        "volume": 80,
        "use_premium_tts": USE_PREMIUM_TTS,
        "widget_pos": None,
    }
    try:
        with open(GUI_CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
            defaults.update(saved)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return defaults


def save_gui_config(config: dict):
    """Persiste configurações da GUI em disco."""
    path = os.path.abspath(GUI_CONFIG_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_audio_devices() -> tuple[list, list]:
    """Retorna (inputs, outputs) como listas de (index, name)."""
    devices = sd.query_devices()
    inputs = []
    outputs = []
    for i, d in enumerate(devices):
        name = d["name"]
        if d["max_input_channels"] > 0:
            inputs.append((i, name))
        if d["max_output_channels"] > 0:
            outputs.append((i, name))
    return inputs, outputs


# ── Estilos ──────────────────────────────────────────────────────────────────

STYLE = """
QDialog {
    background-color: #0D0D0D;
    color: #E0E0E0;
    font-family: 'JetBrains Mono', 'Consolas', 'Courier New', monospace;
    font-size: 12px;
}
QLabel {
    color: #A0A0A0;
    font-size: 11px;
    letter-spacing: 1px;
    text-transform: uppercase;
}
QLabel#title {
    color: #00FF88;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 2px;
}
QLabel#section {
    color: #00FF88;
    font-size: 10px;
    letter-spacing: 3px;
}
QComboBox {
    background-color: #1A1A1A;
    color: #E0E0E0;
    border: 1px solid #2A2A2A;
    border-radius: 0px;
    padding: 6px 10px;
    font-family: 'Consolas', monospace;
    font-size: 11px;
    selection-background-color: #00FF88;
    selection-color: #000000;
}
QComboBox:hover {
    border: 1px solid #00FF88;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #1A1A1A;
    color: #E0E0E0;
    border: 1px solid #2A2A2A;
    selection-background-color: #003322;
    selection-color: #00FF88;
    outline: none;
}
QSlider::groove:horizontal {
    height: 3px;
    background: #2A2A2A;
}
QSlider::handle:horizontal {
    background: #00FF88;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 0px;
}
QSlider::sub-page:horizontal {
    background: #00FF88;
    height: 3px;
}
QCheckBox {
    color: #A0A0A0;
    spacing: 8px;
    font-size: 11px;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #2A2A2A;
    background: #1A1A1A;
    border-radius: 0px;
}
QCheckBox::indicator:checked {
    background: #00FF88;
    border-color: #00FF88;
}
QPushButton#save_btn {
    background-color: #00FF88;
    color: #000000;
    border: none;
    border-radius: 0px;
    padding: 8px 24px;
    font-family: 'Consolas', monospace;
    font-size: 12px;
    font-weight: bold;
    letter-spacing: 2px;
}
QPushButton#save_btn:hover {
    background-color: #00CC66;
}
QPushButton#cancel_btn {
    background-color: transparent;
    color: #606060;
    border: 1px solid #2A2A2A;
    border-radius: 0px;
    padding: 8px 18px;
    font-family: 'Consolas', monospace;
    font-size: 12px;
    letter-spacing: 1px;
}
QPushButton#cancel_btn:hover {
    color: #E0E0E0;
    border-color: #606060;
}
QFrame#separator {
    background-color: #1E1E1E;
    max-height: 1px;
}
"""


class SettingsDialog(QDialog):
    """Modal de configuração de áudio da Kuri."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = load_gui_config()
        self._setup_ui()
        self._load_devices()
        self._restore_selections()

    def _setup_ui(self):
        self.setWindowTitle("KURI — Configurações")
        self.setFixedSize(420, 360)
        self.setStyleSheet(STYLE)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Título
        title = QLabel("⚙  KURI CONFIG")
        title.setObjectName("title")
        layout.addWidget(title)

        sep = QFrame(); sep.setObjectName("separator"); layout.addWidget(sep)

        # ── Entrada de Áudio ──────────────────────────────────────────────
        sec_in = QLabel("// ENTRADA — MICROFONE")
        sec_in.setObjectName("section")
        layout.addWidget(sec_in)

        self.input_combo = QComboBox()
        layout.addWidget(self.input_combo)

        # ── Saída de Áudio ────────────────────────────────────────────────
        sec_out = QLabel("// SAÍDA — ALTO-FALANTE")
        sec_out.setObjectName("section")
        layout.addWidget(sec_out)

        self.output_combo = QComboBox()
        layout.addWidget(self.output_combo)

        sep2 = QFrame(); sep2.setObjectName("separator"); layout.addWidget(sep2)

        # ── Volume ────────────────────────────────────────────────────────
        vol_row = QHBoxLayout()
        vol_label = QLabel("// VOLUME")
        vol_label.setObjectName("section")
        self.vol_value = QLabel(f"{self.config['volume']}%")
        self.vol_value.setStyleSheet("color: #00FF88; font-size: 11px;")
        vol_row.addWidget(vol_label)
        vol_row.addStretch()
        vol_row.addWidget(self.vol_value)
        layout.addLayout(vol_row)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self.config["volume"])
        self.volume_slider.valueChanged.connect(
            lambda v: self.vol_value.setText(f"{v}%")
        )
        layout.addWidget(self.volume_slider)

        sep3 = QFrame(); sep3.setObjectName("separator"); layout.addWidget(sep3)

        # ── TTS Premium ───────────────────────────────────────────────────
        self.premium_check = QCheckBox("Usar ElevenLabs (TTS Premium)")
        self.premium_check.setChecked(self.config.get("use_premium_tts", False))
        layout.addWidget(self.premium_check)

        layout.addStretch()

        # ── Botões ────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel_btn = QPushButton("CANCELAR")
        cancel_btn.setObjectName("cancel_btn")
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("SALVAR")
        save_btn.setObjectName("save_btn")
        save_btn.clicked.connect(self._save_and_close)

        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        # Suporte a arrastar o dialog
        self._drag_pos = None

    def _load_devices(self):
        """Popula os combos com os dispositivos de áudio reais do sistema."""
        self._inputs, self._outputs = get_audio_devices()

        self.input_combo.addItem("Padrão do sistema", None)
        for idx, name in self._inputs:
            self.input_combo.addItem(f"[{idx}] {name}", idx)

        self.output_combo.addItem("Padrão do sistema", None)
        for idx, name in self._outputs:
            self.output_combo.addItem(f"[{idx}] {name}", idx)

    def _restore_selections(self):
        """Restaura seleção salva nos combos."""
        saved_in = self.config.get("input_device")
        saved_out = self.config.get("output_device")

        for i in range(self.input_combo.count()):
            if self.input_combo.itemData(i) == saved_in:
                self.input_combo.setCurrentIndex(i)
                break

        for i in range(self.output_combo.count()):
            if self.output_combo.itemData(i) == saved_out:
                self.output_combo.setCurrentIndex(i)
                break

    def _save_and_close(self):
        self.config["input_device"] = self.input_combo.currentData()
        self.config["output_device"] = self.output_combo.currentData()
        self.config["volume"] = self.volume_slider.value()
        self.config["use_premium_tts"] = self.premium_check.isChecked()
        save_gui_config(self.config)
        self.accept()

    # Suporte a arrastar o dialog (sem borda)
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
