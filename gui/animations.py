"""
animations.py — Helpers para animações Qt na interface da Kuri.
"""

from PyQt6.QtCore import (
    QPropertyAnimation,
    QEasingCurve,
    QPoint,
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


def pulse_glow(shadow_effect, start_blur, end_blur, duration=1000):
    """Anima o blur radius de um efeito de sombra (DropShadow) de forma cíclica."""
    anim = QPropertyAnimation(shadow_effect, b"blurRadius")
    anim.setDuration(duration)
    anim.setStartValue(start_blur)
    anim.setKeyValueAt(0.5, end_blur)
    anim.setEndValue(start_blur)
    anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
    anim.setLoopCount(-1)  # Loop infinito
    anim.start()
    return anim


def fade_slide_in(widget, start_y_offset=20, duration=280):
    """Faz um slide-in e fade-in simultâneo da janela ou widget."""
    opacity_effect = widget.graphicsEffect()
    if not isinstance(opacity_effect, QGraphicsOpacityEffect):
        opacity_effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(opacity_effect)

    anim_fade = QPropertyAnimation(opacity_effect, b"opacity")
    anim_fade.setDuration(duration)
    anim_fade.setStartValue(0.0)
    anim_fade.setEndValue(1.0)
    anim_fade.setEasingCurve(QEasingCurve.Type.OutCubic)

    anim_pos = QPropertyAnimation(widget, b"pos")
    anim_pos.setDuration(duration)
    current_pos = widget.pos()
    anim_pos.setStartValue(QPoint(current_pos.x(), current_pos.y() + start_y_offset))
    anim_pos.setEndValue(current_pos)
    anim_pos.setEasingCurve(QEasingCurve.Type.OutCubic)

    anim_fade.start()
    anim_pos.start()
    return anim_fade, anim_pos


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


def fade_transition(widget, change_callback, duration=240):
    """Executa um fade-out, chama o callback e depois faz fade-in no widget."""
    from PyQt6.QtCore import QSequentialAnimationGroup

    # Cancela animação anterior se houver
    if hasattr(widget, "_current_fade_group") and widget._current_fade_group:
        try:
            widget._current_fade_group.stop()
        except Exception:
            pass

    # Garante o efeito de opacidade
    opacity_effect = widget.graphicsEffect()
    if not isinstance(opacity_effect, QGraphicsOpacityEffect):
        opacity_effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(opacity_effect)

    # Animação de fade-out (opacidade 1 -> 0)
    anim_out = QPropertyAnimation(opacity_effect, b"opacity")
    anim_out.setDuration(duration // 2)
    anim_out.setStartValue(1.0)
    anim_out.setEndValue(0.0)
    anim_out.setEasingCurve(QEasingCurve.Type.OutQuad)

    # Animação de fade-in (opacidade 0 -> 1)
    anim_in = QPropertyAnimation(opacity_effect, b"opacity")
    anim_in.setDuration(duration // 2)
    anim_in.setStartValue(0.0)
    anim_in.setEndValue(1.0)
    anim_in.setEasingCurve(QEasingCurve.Type.InQuad)

    # Conecta o término do fade-out ao callback de mudança
    anim_out.finished.connect(change_callback)

    # Agrupa em sequência
    group = QSequentialAnimationGroup(widget)
    group.addAnimation(anim_out)
    group.addAnimation(anim_in)
    group.start()

    # Guarda a referência da animação
    widget._current_fade_group = group
    return group

