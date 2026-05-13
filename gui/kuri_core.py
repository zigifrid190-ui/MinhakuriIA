"""
kuri_core.py — Loop principal da Kuri adaptado para rodar em thread separada
junto com a GUI PyQt6.

Preserva toda a lógica de stt.py / tts.py / brain.py intacta.
Integra com o bridge para atualizar estado e enviar texto para o widget.
"""

import asyncio
import threading
import sounddevice as sd
from gui.kuri_bridge import KuriState, bridge
from gui.settings_dialog import load_gui_config


def _get_device_index(device_name_or_index) -> int | None:
    """Resolve device para index numérico (None = padrão do sistema)."""
    if device_name_or_index is None:
        return None
    return int(device_name_or_index)


def _apply_audio_config():
    """Aplica o device de saída padrão conforme configuração salva."""
    config = load_gui_config()
    out_idx = _get_device_index(config.get("output_device"))
    if out_idx is not None:
        sd.default.device[1] = out_idx
    in_idx = _get_device_index(config.get("input_device"))
    if in_idx is not None:
        sd.default.device[0] = in_idx


async def _kuri_voice_loop():
    """
    Loop principal de voz da Kuri em modo contínuo.
    Roda como coroutine asyncio dentro de uma thread dedicada.
    """
    from stt import ouvir, SAMPLE_RATE, SILENCE_THRESHOLD, SILENCE_DURATION
    from tts import falar
    from brain import pensar

    # Aplica config de dispositivos de áudio
    _apply_audio_config()

    # Saudação inicial
    bridge.set_state(KuriState.SPEAKING)
    await falar("E aí velho, tô online! Me diz aí o que você precisa.")
    bridge.emit_text("E aí velho, tô online!")
    bridge.set_state(KuriState.IDLE)

    while True:
        # Verifica comando da GUI (ex: shutdown)
        cmd = bridge.get_command(timeout=0.01)
        if cmd == "shutdown":
            break
        if cmd == "stop_listen":
            bridge.set_state(KuriState.IDLE)
            await asyncio.sleep(0.5)
            continue

        # ── Ouvir ──────────────────────────────────────────────────────────
        bridge.set_state(KuriState.LISTENING)
        texto = await asyncio.get_event_loop().run_in_executor(None, ouvir)

        # Verifica shutdown durante gravação
        cmd = bridge.get_command(timeout=0.01)
        if cmd == "shutdown":
            break

        if not texto or not texto.strip():
            bridge.set_state(KuriState.IDLE)
            await asyncio.sleep(0.1)
            continue

        # ── Pensar ─────────────────────────────────────────────────────────
        bridge.set_state(KuriState.THINKING)
        try:
            resultado = await pensar(texto)
            resposta = resultado.get("resposta", "")
            acao = resultado.get("acao_executada")
            emocao = resultado.get("emocao", "neutral")

            if acao:
                bridge.emit_text(f"[AÇÃO] {acao[:50]}")

        except Exception as e:
            bridge.set_state(KuriState.ERROR)
            bridge.set_emotion("angry")
            bridge.emit_text(f"Erro: {str(e)[:50]}")
            await asyncio.sleep(2)
            bridge.set_state(KuriState.IDLE)
            bridge.set_emotion("neutral")
            continue

        # ── Falar ──────────────────────────────────────────────────────────
        if resposta:
            bridge.set_state(KuriState.SPEAKING)
            bridge.set_emotion(emocao)
            bridge.emit_text(resposta)
            
            # Carrega config da GUI para ver se deve usar premium
            config = load_gui_config()
            usar_premium = config.get("use_premium_tts", False)
            
            await falar(resposta, premium=usar_premium)

        bridge.set_state(KuriState.IDLE)
        bridge.set_emotion("neutral")
        # Removido sleep para resposta imediata


def start_core_thread():
    """
    Inicia o loop asyncio do core em uma thread daemon separada.
    Retorna a thread para controle externo.
    """
    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_kuri_voice_loop())
        except Exception as e:
            print(f"[CORE] Erro fatal no loop: {e}")
            bridge.set_state(KuriState.ERROR)
        finally:
            loop.close()

    thread = threading.Thread(target=_run, daemon=True, name="KuriCore")
    thread.start()
    return thread
