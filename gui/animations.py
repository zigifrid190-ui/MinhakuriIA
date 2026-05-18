"""
animations.py — Helpers para animações Qt na interface da Kuri.
"""

from PyQt6.QtCore import (
    QPropertyAnimation,
    QEasingCurve,
)
from PyQt6.QtWidgets import QGraphicsOpacityEffect


def fade_in(widget, duration=500):
    """Efeito de fade-in suave."""
    opacity_effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(opacity_effect)

    anim = QPropertyAnimation(opacity_effect, b"opacity")
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
    anim.start()
    return anim


def pulse_glow(widget, start_color, end_color, duration=1000):
    """Cria uma animação de pulsação de cor/glow (necessita QSS properties)."""
    # Em Qt, animações de cor em QSS exigem custom properties ou herança de QWidget
    # Para simplicidade, vamos animar a opacidade de uma borda ou sombra futuramente.
    pass


def smooth_resize(widget, start_height, end_height, duration=300):
    """Anima a altura de um widget de forma suave."""
    anim = QPropertyAnimation(widget, b"minimumHeight")
    anim.setDuration(duration)
    anim.setStartValue(start_height)
    anim.setEndValue(end_height)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.start()

    # Também anima o maximumHeight para garantir que ele mude
    anim_max = QPropertyAnimation(widget, b"maximumHeight")
    anim_max.setDuration(duration)
    anim_max.setStartValue(start_height)
    anim_max.setEndValue(end_height)
    anim_max.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim_max.start()

    return anim, anim_max
