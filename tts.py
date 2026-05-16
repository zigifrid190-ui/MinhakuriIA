import asyncio
import edge_tts
import os
import io
import httpx
import pygame
import hashlib
import re
from config import (
    EDGE_TTS_VOICE, USE_PREMIUM_TTS,
    ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID
)

# Inicializa pygame mixer uma vez
pygame.mixer.init()

# Configurações de Cache
CACHE_DIR = "tts_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

VOICE_PROFILES = {
    "neutral":   {"stability": 0.75, "similarity_boost": 0.8, "style": 0.5},
    "cool":      {"stability": 0.7,  "similarity_boost": 0.8, "style": 0.6},
    "surprised": {"stability": 0.5,  "similarity_boost": 0.9, "style": 0.8},
    "blushing":  {"stability": 0.85, "similarity_boost": 0.8, "style": 0.4},
    "angry":     {"stability": 0.4,  "similarity_boost": 0.9, "style": 0.9},
}

EDGE_TTS_PROFILES = {
    "neutral":   {"rate": "-10%", "pitch": "+0Hz"},
    "cool":      {"rate": "-15%", "pitch": "-2Hz"},
    "surprised": {"rate": "+5%",  "pitch": "+5Hz"},
    "blushing":  {"rate": "-10%", "pitch": "+2Hz"},
    "angry":     {"rate": "+10%", "pitch": "-5Hz"},
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
    sentencas = [s.strip() for s in re.split(r'(?<=[.!?]) +', texto) if s.strip()]
    
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
        communicate = edge_tts.Communicate(texto, EDGE_TTS_VOICE, rate=perfil["rate"], pitch=perfil["pitch"])
        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.write(chunk["data"])
        
        audio_data.seek(0)
        _reproduzir_buffer(audio_data)
    except Exception as e:
        print(f"[ERRO] edge-tts: {e}")

async def _falar_elevenlabs(texto: str, emocao: str):
    """TTS premium ElevenLabs com cache local."""
    try:
        # Usamos a emoção no hash para que a mesma frase com emoções diferentes não reuse o cache
        hash_content = f"{emocao}_{texto}"
        text_hash = hashlib.md5(hash_content.encode('utf-8')).hexdigest()
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
                    "voice_settings": voice_settings
                }
            )
            response.raise_for_status()
            
            # ElevenLabs ainda salvamos em cache para economia futura
            with open(cache_path, "wb") as f:
                f.write(response.content)
            
            _reproduzir_audio_file(cache_path)
            
    except Exception as e:
        print(f"[ERRO] ElevenLabs: {e}")
        await _falar_edge_tts(texto, emocao)

def _reproduzir_buffer(buffer: io.BytesIO):
    """Toca áudio direto do buffer de memória."""
    try:
        pygame.mixer.music.load(buffer)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(50)
    except Exception as e:
        print(f"[ERRO] Reprodução buffer: {e}")
    finally:
        pygame.mixer.music.unload()

def _reproduzir_audio_file(path: str):
    """Toca arquivo de áudio local."""
    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(50)
    except Exception as e:
        print(f"[ERRO] Reprodução arquivo: {e}")
    finally:
        pygame.mixer.music.unload()
