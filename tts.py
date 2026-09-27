import asyncio
import edge_tts
import os
import io
import httpx
import pygame
import hashlib
import re
import numpy as np
from config import (
    EDGE_TTS_VOICE,
    USE_PREMIUM_TTS,
    ELEVENLABS_API_KEY,
    ELEVENLABS_VOICE_ID,
)
from logger import get_logger

log = get_logger("tts")

# Inicializa pygame mixer com tratamento de erros caso não haja saída de áudio
try:
    pygame.mixer.init()
    _mixer_initialized = True
except Exception as e:
    log.error(f"Não foi possível inicializar o mixer de áudio (saída): {e}")
    _mixer_initialized = False

# Configurações de Cache
CACHE_DIR = "tts_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

VOICE_PROFILES = {
    "neutral": {"stability": 0.75, "similarity_boost": 0.8, "style": 0.5},
    "cool": {"stability": 0.7, "similarity_boost": 0.8, "style": 0.6},
    "surprised": {"stability": 0.5, "similarity_boost": 0.9, "style": 0.8},
    "blushing": {"stability": 0.85, "similarity_boost": 0.8, "style": 0.4},
    "angry": {"stability": 0.4, "similarity_boost": 0.9, "style": 0.9},
}

EDGE_TTS_PROFILES = {
    "neutral": {"rate": "-10%", "pitch": "+0Hz"},
    "cool": {"rate": "-15%", "pitch": "-2Hz"},
    "surprised": {"rate": "+5%", "pitch": "+5Hz"},
    "blushing": {"rate": "-10%", "pitch": "+2Hz"},
    "angry": {"rate": "+10%", "pitch": "-5Hz"},
}


async def falar(texto: str, premium: bool | None = None, emocao: str = "neutral"):
    """Converte texto em voz e reproduz localmente com streaming por sentenças."""
    usar_premium = premium if premium is not None else USE_PREMIUM_TTS

    # Se o texto for muito curto, fala direto
    if len(texto) < 50:
        await _processar_fala(texto, usar_premium, emocao)
        return

    # Split por sentenças para "streaming" de percepção
    # (O usuário ouve a primeira frase enquanto as outras são processadas)
    sentencas = [s.strip() for s in re.split(r"(?<=[.!?]) +", texto) if s.strip()]

    for i, sentenca in enumerate(sentencas):
        await _processar_fala(sentenca, usar_premium, emocao)
        # Adiciona uma pequena pausa entre sentenças para não parecer "corrida"
        if i < len(sentencas) - 1:
            await asyncio.sleep(0.4)


async def _processar_fala(texto: str, usar_premium: bool, emocao: str):
    """Encaminha para o motor correto."""
    if usar_premium and ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID:
        await _falar_elevenlabs(texto, emocao)
    else:
        await _falar_edge_tts(texto, emocao)


async def _falar_edge_tts(texto: str, emocao: str):
    """TTS gratuito via edge-tts com buffer em memória (sem escrita em disco)."""
    try:
        perfil = EDGE_TTS_PROFILES.get(emocao, EDGE_TTS_PROFILES["neutral"])
        communicate = edge_tts.Communicate(
            texto, EDGE_TTS_VOICE, rate=perfil["rate"], pitch=perfil["pitch"]
        )
        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.write(chunk["data"])

        audio_data.seek(0)
        _reproduzir_buffer(audio_data)
    except Exception as e:
        log.error(f"edge-tts: {e}")


async def _falar_elevenlabs(texto: str, emocao: str):
    """TTS premium ElevenLabs com cache local."""
    try:
        # Usamos a emoção no hash para que a mesma frase com emoções diferentes não reuse o cache
        hash_content = f"{emocao}_{texto}"
        # Bandit B324 fix: use sha256 instead of md5
        text_hash = hashlib.sha256(hash_content.encode('utf-8')).hexdigest()
        cache_path = os.path.join(CACHE_DIR, f"{text_hash}.mp3")

        if os.path.exists(cache_path):
            _reproduzir_audio_file(cache_path)
            return

        voice_settings = VOICE_PROFILES.get(emocao, VOICE_PROFILES["neutral"])

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
                headers={"xi-api-key": ELEVENLABS_API_KEY},
                json={
                    "text": texto,
                    "model_id": "eleven_turbo_v2_5",
                    "voice_settings": voice_settings,
                },
            )
            response.raise_for_status()

            # ElevenLabs ainda salvamos em cache para economia futura
            with open(cache_path, "wb") as f:
                f.write(response.content)

            _reproduzir_audio_file(cache_path)

    except Exception as e:
        log.error(f"ElevenLabs: {e}")
        await _falar_edge_tts(texto, emocao)


def _envelope_from_sound_bytes(raw: bytes, frame_s: float = 0.05) -> list[float] | None:
    """RMS por fatia ~50ms para lip sync. None se o pygame não decodificar."""
    if not _mixer_initialized or not raw:
        return None
    try:
        sound = pygame.mixer.Sound(io.BytesIO(raw))
        arr = np.asarray(pygame.sndarray.array(sound), dtype=np.float32)
        if arr.ndim > 1:
            arr = arr.mean(axis=1)
        peak = float(np.max(np.abs(arr))) or 1.0
        arr = arr / peak
        init = pygame.mixer.get_init()
        sr = int(init[0]) if init else 22050
        win = max(1, int(sr * frame_s))
        frames = []
        for i in range(0, max(1, len(arr) - win + 1), win):
            chunk = arr[i : i + win]
            rms = float(np.sqrt(np.mean(chunk * chunk)))
            frames.append(min(1.0, rms * 2.8))
        return frames or None
    except Exception as e:
        log.debug(f"envelope de áudio indisponível: {e}")
        return None


def _drive_mouth(envelope: list[float] | None, elapsed_s: float, frame_s: float = 0.05) -> None:
    try:
        from gui.kuri_bridge import bridge
    except Exception:
        return
    if envelope:
        idx = min(len(envelope) - 1, max(0, int(elapsed_s / frame_s)))
        bridge.set_mouth(envelope[idx])
    else:
        # Fallback: pulso no tempo de playback, não no tick do Live2D
        import math
        bridge.set_mouth(0.22 + 0.28 * (0.5 + 0.5 * math.sin(elapsed_s * 14.0)))


def _reproduzir_pcm_like(load_fn, envelope: list[float] | None):
    """Toca e empurra a boca no ritmo do áudio. load_fn carrega no mixer.music."""
    from kuri_runtime import set_speaking

    if not _mixer_initialized:
        log.warning("Mixer de áudio não inicializado. Pulando reprodução.")
        import time
        time.sleep(1.0)
        return
    try:
        try:
            from gui.kuri_bridge import KuriState, bridge
            bridge.set_state(KuriState.SPEAKING)
        except Exception:
            pass
        set_speaking(True)
        load_fn()
        pygame.mixer.music.play()
        t0 = pygame.time.get_ticks()
        while pygame.mixer.music.get_busy():
            elapsed = (pygame.time.get_ticks() - t0) / 1000.0
            _drive_mouth(envelope, elapsed)
            pygame.time.wait(30)
    except Exception as e:
        log.error(f"Reprodução: {e}")
    finally:
        set_speaking(False)
        try:
            from gui.kuri_bridge import KuriState, bridge
            bridge.set_mouth(0.0)
            bridge.set_state(KuriState.THINKING)
        except Exception:
            pass
        try:
            pygame.mixer.music.unload()
        except Exception:
            pass


def _reproduzir_buffer(buffer: io.BytesIO):
    """Toca áudio direto do buffer de memória."""
    raw = buffer.getvalue()
    envelope = _envelope_from_sound_bytes(raw)
    replay = io.BytesIO(raw)
    _reproduzir_pcm_like(lambda: pygame.mixer.music.load(replay), envelope)


def _reproduzir_audio_file(path: str):
    """Toca arquivo de áudio local."""
    raw = b""
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except Exception:
        pass
    envelope = _envelope_from_sound_bytes(raw) if raw else None
    _reproduzir_pcm_like(lambda: pygame.mixer.music.load(path), envelope)


async def falar_stream(sentenca_generator, premium: bool | None = None):
    """
    Consome um async generator de sentenças (do pensar_stream) e fala cada
    uma imediatamente. O usuário ouve a primeira frase enquanto o LLM
    ainda gera o restante.

    Args:
        sentenca_generator: async generator que yield dicts com
            {"sentenca": str, "emocao": str, "final": bool}
        premium: forçar ElevenLabs ou não (None = usar config global)

    Returns:
        dict com {"resposta_completa": str, "emocao": str, "acao_executada": str | None}
    """
    usar_premium = premium if premium is not None else USE_PREMIUM_TTS
    resposta_completa = []
    emocao_final = "neutral"
    acao_executada = None

    async for chunk in sentenca_generator:
        sentenca = chunk.get("sentenca", "")
        emocao = chunk.get("emocao", "neutral")
        emocao_final = emocao
        acao_executada = chunk.get("acao_executada", acao_executada)

        if sentenca:
            resposta_completa.append(sentenca)
            await _processar_fala(sentenca, usar_premium, emocao)

    return {
        "resposta_completa": " ".join(resposta_completa),
        "emocao": emocao_final,
        "acao_executada": acao_executada,
    }

