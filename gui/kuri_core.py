"""
kuri_core.py — Loop principal da Kuri adaptado para rodar em thread separada
junto com a GUI PyQt6.

Preserva toda a lógica de stt.py / tts.py / brain.py intacta.
Integra com o bridge para atualizar estado e enviar texto para o widget.
"""

import asyncio
import threading
import time
import sounddevice as sd
from gui.kuri_bridge import KuriState, bridge
from gui.settings_dialog import load_gui_config
import routines
from logger import get_logger
from kuri_runtime import (
    is_wake_word,
    open_conversation,
    conversation_open,
    process_utterance,
    is_kuri_speaking,
)

log = get_logger("core")

# Sleep mode tracking (baixo consumo)
_last_activity = time.time()
_in_sleep = False
_consecutive_silence = 0
_mic_check_attempts = 0
_mic_suspended = False

from config import (
    SLEEP_TIMEOUT_MINUTES,
    MAX_MIC_VERIFICATION_ATTEMPTS, MAX_CONSECUTIVE_SILENCE, SLEEP_LISTEN_INTERVAL,
)

def _update_activity():
    global _last_activity, _in_sleep, _consecutive_silence, _mic_check_attempts, _mic_suspended
    _last_activity = time.time()
    _consecutive_silence = 0
    _mic_check_attempts = 0
    open_conversation()
    if _in_sleep:
        _in_sleep = False
        bridge.set_state(KuriState.IDLE)
        log.info("Saindo do modo sono (atividade detectada)")
    if _mic_suspended:
        _mic_suspended = False
        log.info("Retomando verificações de microfone")

def _should_enter_sleep() -> bool:
    if _in_sleep:
        return False
    idle_minutes = (time.time() - _last_activity) / 60
    return idle_minutes > SLEEP_TIMEOUT_MINUTES


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
    global _in_sleep, _consecutive_silence, _mic_check_attempts, _mic_suspended

    from stt import ouvir, calibrar_microfone, is_microphone_available
    from tts import falar

    # Aplica config de dispositivos de áudio
    _apply_audio_config()

    # Verifica se há microfone disponível (com suporte a suspensão)
    if not is_microphone_available():
        _mic_check_attempts += 1
        if _mic_check_attempts > MAX_MIC_VERIFICATION_ATTEMPTS:
            _mic_suspended = True
            _in_sleep = True
            bridge.set_state(KuriState.SLEEPING)
            bridge.set_emotion("neutral")
            bridge.emit_text("[Nenhum microfone detectado após várias tentativas. Suspenso. Diga 'acorda Kuri' ou aguarde.]")
            try:
                await falar("Não estou conseguindo captar o microfone agora. Vou entrar em modo de espera.")
            except:
                pass
            await asyncio.sleep(5)
        else:
            log.warning("Nenhum microfone funcional foi detectado.")
            bridge.set_state(KuriState.IDLE)
            bridge.set_emotion("neutral")
            bridge.emit_text("[Microfone não detectado no momento... vou ficar em standby.]")
            try:
                await falar("Não estou ouvindo o microfone. Vou ficar em standby por enquanto.")
            except:
                pass
            await asyncio.sleep(4.0)
    else:
        # Calibração inicial (opcional, para definir sensibilidade)
        bridge.set_state(KuriState.THINKING)
        bridge.emit_text("[Calibrando microfone...]")
        await calibrar_microfone(duration=1.5)
        # Saudação inicial
        bridge.set_state(KuriState.SPEAKING)
        await falar("E aí velho, tô online! Me diz aí o que você precisa.")
        bridge.emit_text("E aí velho, tô online!")

    bridge.set_state(KuriState.IDLE)

    proativo = None
    while True:
        # Verifica comando da GUI (ex: shutdown, sleep)
        cmd = bridge.get_command(timeout=0.01)
        if cmd == "shutdown":
            break
        if cmd == "stop_listen":
            bridge.set_state(KuriState.IDLE)
            await asyncio.sleep(0.5)
            continue
        if cmd == "sleep":
            _in_sleep = True
            _consecutive_silence = 0
            bridge.set_state(KuriState.SLEEPING)
            bridge.emit_text("[Entrando em modo sono manualmente]")
            await asyncio.sleep(1)
            continue
        if cmd == "wake":
            _update_activity()
            _in_sleep = False
            _mic_suspended = False
            _mic_check_attempts = 0
            bridge.set_state(KuriState.IDLE)
            bridge.emit_text("Acordei!")
            continue

        # Se em sono ou mic suspenso, suspende verificações pesadas (baixo consumo)
        # Não chama ouvir() para evitar loop constante de seleção de dispositivo
        if _in_sleep or _mic_suspended:
            sleep_time = 30.0 if _mic_suspended else SLEEP_LISTEN_INTERVAL
            await asyncio.sleep(sleep_time)

            # Verifica time-based sleep mesmo no branch suspenso
            if _should_enter_sleep() and not _in_sleep:
                _in_sleep = True
                bridge.set_state(KuriState.SLEEPING)
                bridge.set_emotion("neutral")
                log.info("Entrando em modo sono por tempo de inatividade")

            # Opcional: rechecar mic periodicamente se suspenso
            if _mic_suspended:
                log.info("Mic suspenso - verificações pausadas. Aguardando wake ou recheck.")
                _mic_check_attempts = 0
                # Re-force SLEEPING state so the avatar keeps the custom sleep animation
                # (prevents idle motion from taking over again).
                # See docs/SLEEP_MODE_FIX.md (search: SLEEP_VISUAL_PERSIST)
                bridge.set_state(KuriState.SLEEPING)
                bridge.set_emotion("neutral")
                continue

            # Em sono normal (não suspenso por mic), fazemos check leve para wake
            bridge.set_state(KuriState.LISTENING)
            texto = await asyncio.get_event_loop().run_in_executor(None, ouvir)
            if is_wake_word(texto):
                _update_activity()
                _in_sleep = False
                _consecutive_silence = 0
                _mic_suspended = False
                bridge.set_state(KuriState.IDLE)
                bridge.set_emotion("neutral")
                bridge.emit_text("Acordei! O que precisa, velho?")
                await asyncio.sleep(0.3)
                # continua para processar
            else:
                continue

        # ── Ouvir normal (com limite de verificações) ────────────────────────
        if _mic_check_attempts > MAX_MIC_VERIFICATION_ATTEMPTS:
            _mic_suspended = True
            _in_sleep = True
            bridge.set_state(KuriState.SLEEPING)
            bridge.set_emotion("neutral")
            bridge.emit_text("[Verificações de microfone suspensas após máximo de tentativas. Modo sono/aguardando.]")
            try:
                await falar("Não estou identificando o microfone. Suspensei as verificações e entrei em modo de espera.")
            except:
                pass
            await asyncio.sleep(5)
            continue

        if is_kuri_speaking():
            await asyncio.sleep(0.2)
            continue

        bridge.set_state(KuriState.LISTENING)
        texto = await asyncio.get_event_loop().run_in_executor(None, ouvir)
        _mic_check_attempts += 1

        # Verifica shutdown durante gravação
        cmd = bridge.get_command(timeout=0.01)
        if cmd == "shutdown":
            break

        if not texto or not texto.strip():
            _consecutive_silence += 1
            if _consecutive_silence > MAX_CONSECUTIVE_SILENCE:
                _in_sleep = True
                _consecutive_silence = 0
                bridge.set_state(KuriState.SLEEPING)
                bridge.set_emotion("neutral")
                bridge.emit_text("[Modo sono ativado por falta de interação - verificações suspensas.]")
                await asyncio.sleep(2)
                continue

            # Tenta disparar uma interação proativa
            proativo = await routines.check_proactivity()
            if proativo:
                texto = proativo
                bridge.emit_text("[Iniciando conversa proativa...]")
            else:
                bridge.set_state(KuriState.IDLE)
                await asyncio.sleep(2.0)
                continue
        else:
            _consecutive_silence = 0
            _mic_check_attempts = 0  # reset on successful input

        # ── Filtro de atenção ──────────────────────────────────────────────
        # Sono: precisa acordar pelo nome/frase.
        # Conversa aberta ou fala proativa: ela já está na sala.
        woke = is_wake_word(texto)
        is_proactive = bool(proativo) and texto == proativo

        if _in_sleep and not woke:
            log.info(f"Em sono, sem frase de acordar. Ignorando: '{texto}'")
            continue

        if not _in_sleep and not woke and not is_proactive and not conversation_open():
            log.info(f"Fora da janela de conversa. Chama ela pelo nome: '{texto}'")
            bridge.emit_text(f"[Ouvi: {texto[:80]}] Me chama de Kuri.")
            bridge.set_state(KuriState.IDLE)
            continue

        # ── Pensar + Falar (mesmo caminho do CLI) ──────────────────────────
        bridge.set_state(KuriState.THINKING)
        try:
            config = load_gui_config()
            usar_premium = config.get("use_premium_tts", False)

            def _on_chunk(chunk: dict):
                emocao_c = chunk.get("emocao", "neutral")
                sentenca_c = chunk.get("sentenca", "")
                bridge.set_emotion(emocao_c)
                if sentenca_c:
                    bridge.emit_text(sentenca_c)

            resultado = await process_utterance(
                texto,
                premium=usar_premium,
                chunk_hook=_on_chunk,
            )

            resposta = resultado.get("resposta_completa", "")
            acao = resultado.get("acao_executada")
            emocao = resultado.get("emocao", "neutral")

            if resposta:
                bridge.emit_text(resposta[:100])
            if acao:
                bridge.emit_text(f"[AÇÃO] {acao[:80]}")
                log.info(f"Ação no widget: {acao}")
            if emocao:
                bridge.set_emotion(emocao)

        except Exception as e:
            bridge.set_state(KuriState.IDLE)
            bridge.set_emotion("neutral")
            bridge.emit_text(f"Erro temporário: {str(e)[:50]}. Voltando ao normal.")
            await asyncio.sleep(2)
            bridge.set_state(KuriState.IDLE)
            continue

        bridge.set_state(KuriState.IDLE)
        _update_activity()
        open_conversation()

        # Verifica entrada em modo sono para economia de CPU
        if _should_enter_sleep():
            _in_sleep = True
            bridge.set_state(KuriState.SLEEPING)
            bridge.set_emotion("neutral")  # garante que não fica em angry ou outra
            bridge.emit_text("[Modo sono ativado - baixo consumo. Diga 'acorda Kuri' para me acordar]")
            log.info("Entrando em modo sono (baixo consumo)")
            await asyncio.sleep(1.0)


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
            log.critical(f"Erro fatal no loop: {e}")
            bridge.set_state(KuriState.IDLE)
            bridge.set_emotion("neutral")
        finally:
            loop.close()

    thread = threading.Thread(target=_run, daemon=True, name="KuriCore")
    thread.start()
    return thread
