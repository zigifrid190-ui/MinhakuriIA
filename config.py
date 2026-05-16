import os
import torch
from dotenv import load_dotenv

from path_utils import get_resource_path

load_dotenv(get_resource_path(".env"))

# ===== API Keys =====
GROK_API_KEY = os.getenv("GROK_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")

# ===== Performance Mode =====
# low: hardware modesto, balanced: padrão, high: hardware potente
KURI_PERF_MODE = os.getenv("KURI_PERF_MODE", "balanced").lower()

# ===== GPU Detection =====
HAS_CUDA = torch.cuda.is_available()

# ===== LLM =====
GROK_MODEL = "grok-4"
GROK_TEMPERATURE = 0.88
GROK_MAX_TOKENS = 200
GROK_URL = "https://api.x.ai/v1/chat/completions"

# ===== TTS =====
EDGE_TTS_VOICE = "pt-BR-FranciscaNeural"
TTS_OUTPUT_FILE = "kuri_resposta.mp3"
USE_PREMIUM_TTS = os.getenv("USE_PREMIUM_TTS", "false").lower() == "true"

# ===== STT =====
# tiny, base, small, medium, large-v3
if KURI_PERF_MODE == "low":
    WHISPER_MODEL = "tiny"
    CPU_THREADS = 2
elif KURI_PERF_MODE == "high":
    WHISPER_MODEL = "small"
    CPU_THREADS = 8
else: # balanced
    WHISPER_MODEL = "base"
    CPU_THREADS = 4

WHISPER_DEVICE = "cuda" if HAS_CUDA else "cpu"
WHISPER_COMPUTE = "float16" if HAS_CUDA else "int8"
WHISPER_LANGUAGE = "pt"

# ===== Memory =====
# Banco de dados SQLite para persistência
KURI_DB = "kuri_memory.db"
MAX_MEMORY_MESSAGES = 50
CONTEXT_WINDOW = 20           # últimas N mensagens enviadas para o LLM

# ===== Prompt =====
PROMPT_FILE = get_resource_path("prompt_kuri.txt")

# ===== System =====
SILENCE_TIMEOUT = 8.0         # segundos de silêncio antes de "dormir"
