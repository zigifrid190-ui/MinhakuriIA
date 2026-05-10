import os
from dotenv import load_dotenv

from path_utils import get_resource_path

load_dotenv(get_resource_path(".env"))

# ===== API Keys =====
GROK_API_KEY = os.getenv("GROK_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")

# ===== LLM =====
GROK_MODEL = "grok-4"
GROK_TEMPERATURE = 0.88
GROK_MAX_TOKENS = 450
GROK_URL = "https://api.x.ai/v1/chat/completions"

# ===== TTS =====
EDGE_TTS_VOICE = "pt-BR-FranciscaNeural"
TTS_OUTPUT_FILE = "kuri_resposta.mp3"
USE_PREMIUM_TTS = False  # True = ElevenLabs, False = edge-tts (gratuito)

# ===== STT =====
WHISPER_MODEL = "base"        # tiny, base, small, medium, large-v3
WHISPER_DEVICE = "cpu"        # cpu ou cuda (se tiver GPU NVIDIA)
WHISPER_COMPUTE = "int8"      # int8 (CPU rápido) ou float16 (GPU)
WHISPER_LANGUAGE = "pt"

# ===== Memory =====
# Estes ficam fora do bundle para persistência
MEMORY_FILE = "kuri_memoria.json"
PROFILE_FILE = "kuri_perfil.json"
MAX_MEMORY_MESSAGES = 50
CONTEXT_WINDOW = 20           # últimas N mensagens enviadas para o LLM

# ===== Prompt =====
PROMPT_FILE = get_resource_path("prompt_kuri.txt")

# ===== System =====
SILENCE_TIMEOUT = 8.0         # segundos de silêncio antes de "dormir"
