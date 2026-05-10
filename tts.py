import asyncio
import edge_tts
import os
import io
import httpx
import pygame
from config import (
    EDGE_TTS_VOICE, TTS_OUTPUT_FILE, USE_PREMIUM_TTS,
    ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID
)

# Inicializa pygame mixer uma vez
pygame.mixer.init()


async def falar(texto: str, premium: bool | None = None):
    """Converte texto em voz e reproduz localmente."""
    usar_premium = premium if premium is not None else USE_PREMIUM_TTS

    if usar_premium and ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID:
        await _falar_elevenlabs(texto)
    else:
        await _falar_edge_tts(texto)


async def _falar_edge_tts(texto: str):
    """TTS gratuito via edge-tts (Microsoft) — boa qualidade, custo zero."""
    try:
        communicate = edge_tts.Communicate(texto, EDGE_TTS_VOICE)
        await communicate.save(TTS_OUTPUT_FILE)
        _reproduzir_audio(TTS_OUTPUT_FILE)
    except Exception as e:
        print(f"[ERRO] edge-tts: {e}")


async def _falar_elevenlabs(texto: str):
    """TTS premium via ElevenLabs — voz ultra-realista."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
                headers={"xi-api-key": ELEVENLABS_API_KEY},
                json={
                    "text": texto,
                    "model_id": "eleven_turbo_v2_5",
                    "voice_settings": {
                        "stability": 0.65,
                        "similarity_boost": 0.85,
                        "style": 0.8
                    }
                }
            )
            response.raise_for_status()
            with open(TTS_OUTPUT_FILE, "wb") as f:
                f.write(response.content)
            _reproduzir_audio(TTS_OUTPUT_FILE)
    except Exception as e:
        print(f"[ERRO] ElevenLabs, fallback para edge-tts: {e}")
        await _falar_edge_tts(texto)


def _reproduzir_audio(path: str):
    """Toca o arquivo de áudio localmente via pygame."""
    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(50)
    except Exception as e:
        print(f"[ERRO] Ao reproduzir audio: {e}")
    finally:
        pygame.mixer.music.unload()
        # Limpa o arquivo temporário
        try:
            os.remove(path)
        except OSError:
            pass
