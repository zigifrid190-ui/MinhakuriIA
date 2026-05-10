"""
kuri_desktop.py — Entrypoint do widget desktop da Kuri.

Uso:
    python kuri_desktop.py

Inicia:
    1. Thread daemon do core Python (asyncio: stt → brain → tts)
    2. Aplicação PyQt6 com o widget flutuante
"""

import sys
import os

# Garante que o diretório raiz do projeto esteja no path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from gui.widget import KuriWidget
from gui.kuri_core import start_core_thread


def main():
    # ── Inicia core Python em thread daemon ───────────────────────────────────
    print("[KURI] Iniciando core de voz...")
    core_thread = start_core_thread()

    # ── Inicia aplicação PyQt6 ────────────────────────────────────────────────
    app = QApplication(sys.argv)
    app.setApplicationName("Kuri")
    app.setApplicationDisplayName("Kuri IA")

    # Evita fechar o app ao fechar outros dialogs
    app.setQuitOnLastWindowClosed(False)

    widget = KuriWidget()
    widget.show()

    print("[KURI] Widget iniciado! Aguardando o core carregar o Whisper...")
    exit_code = app.exec()

    # Aguarda thread terminar graciosamente (máx 3s)
    core_thread.join(timeout=3.0)
    print("[KURI] Encerrada. Até mais, velho!")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
