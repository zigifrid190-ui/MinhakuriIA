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
import multiprocessing

def main():
    # ── SUPORTE A MULTIPROCESSAMENTO NO WINDOWS (MANDATÓRIO ANTES DE QUALQUER OUTRA AÇÃO) ──
    multiprocessing.freeze_support()

    # Evita falhas de duplicação do runtime do OpenMP no Windows
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    # Força single-thread OpenMP para evitar conflito de DLLs no bundle congelado
    os.environ["OMP_NUM_THREADS"] = "1"

    # Garante que o diretório raiz do projeto esteja no path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    # ── 1. IMPORTS E INICIALIZAÇÃO DE IA (CTranslate2 / Torch) ──
    # Inicializa o Whisper na thread principal antes de carregar DLLs gráficas para evitar conflitos no Windows
    from stt import _get_model
    print("[KURI] Pré-carregando motor de voz Whisper...")
    try:
        _get_model()
    except Exception as e:
        print(f"[KURI] Aviso ao carregar Whisper no startup: {e}")

    # ── 2. IMPORTS GRÁFICOS ──
    from PyQt6.QtWidgets import QApplication
    from gui.widget import KuriWidget
    from gui.kuri_core import start_core_thread
    from gui.live2d_avatar import shutdown_live2d

    # ── Inicia core Python em thread daemon ──
    print("[KURI] Iniciando core de voz...")
    core_thread = start_core_thread()

    # ── Inicia aplicação PyQt6 ────────────────────────────────────────────────
    app = QApplication(sys.argv)
    app.setApplicationName("Kuri")
    app.setApplicationDisplayName("Kuri IA")

    # Evita fechar o app ao fechar outros dialogs
    app.setQuitOnLastWindowClosed(False)

    try:
        widget = KuriWidget()
        widget.show()
    except Exception as exc:
        print(f"[KURI] Falha ao abrir widget: {exc}")
        shutdown_live2d()
        sys.exit(1)

    print("[KURI] Widget iniciado! Aguardando o core carregar o Whisper...")
    exit_code = app.exec()

    # Aguarda thread terminar graciosamente (máx 3s)
    core_thread.join(timeout=3.0)
    shutdown_live2d()
    print("[KURI] Encerrada. Até mais, velho!")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
