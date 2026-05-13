import asyncio
import edge_tts
import os
import io
import httpx
import pygame
import hashlib
from config import (
    EDGE_TTS_VOICE, TTS_OUTPUT_FILE, USE_PREMIUM_TTS,
    ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID
)

# Inicializa pygame mixer uma vez
pygame.mixer.init()

# Configurações de Cache
CACHE_DIR = "tts_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

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
        _reproduzir_audio(TTS_OUTPUT_FILE, delete_after=True)
    except Exception as e:
        print(f"[ERRO] edge-tts: {e}")


async def _falar_elevenlabs(texto: str):
    """TTS premium via ElevenLabs — voz ultra-realista com cache local."""
    try:
        # Gerar hash para o cache
        text_hash = hashlib.md5(texto.encode('utf-8')).hexdigest()
        cache_path = os.path.join(CACHE_DIR, f"{text_hash}.mp3")

        # Se já estiver no cache, apenas reproduz
        if os.path.exists(cache_path):
            _reproduzir_audio(cache_path, delete_after=False)
            return

        # Caso contrário, chama a API
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
            
            with open(cache_path, "wb") as f:
                f.write(response.content)
            
            _reproduzir_audio(cache_path, delete_after=False)
            
    except Exception as e:
        print(f"[ERRO] ElevenLabs, fallback para edge-tts: {e}")
        await _falar_edge_tts(texto)


def _reproduzir_audio(path: str, delete_after: bool = True):
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
        if delete_after:
            try:
                os.remove(path)
            except OSError:
                pass
