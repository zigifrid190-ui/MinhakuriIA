"""Smoke test do avatar Live2D da Kuri."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from gui.live2d_avatar import Live2DAvatarWidget, can_use_live2d_avatar, shutdown_live2d


def main():
    if not can_use_live2d_avatar():
        print("Live2D indisponível — verifique live2d-py e assets/live2d/kuri_model")
        return 1

    app = QApplication(sys.argv)
    widget = Live2DAvatarWidget()
    widget.setWindowTitle("Kuri Live2D Test — arraste o canto para redimensionar")
    widget.resize(156, 156)
    widget.setMinimumSize(96, 96)
    widget.setMaximumSize(440, 440)
    widget.show()
    widget.set_emotion("blushing")

    code = app.exec()
    shutdown_live2d()
    return code


if __name__ == "__main__":
    raise SystemExit(main())