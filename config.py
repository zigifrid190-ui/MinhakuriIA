import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
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
GROK_MODEL = os.getenv("GROK_MODEL", "grok-4-fast")
GROK_TEMPERATURE = 0.88
GROK_MAX_TOKENS = 450
GROK_URL = "https://api.x.ai/v1/chat/completions"
GROK_CONNECT_TIMEOUT = 10.0
GROK_READ_TIMEOUT = 90.0

# ===== Ollama (Fallback Local) =====
OLLAMA_ENABLED = os.getenv("OLLAMA_ENABLED", "true").lower() == "true"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")
OLLAMA_API_URL = f"{OLLAMA_URL}/v1/chat/completions"  # OpenAI-compatible endpoint

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
else:  # balanced
    WHISPER_MODEL = "base"
    CPU_THREADS = 4

# Força CPU para o Whisper para evitar falhas do CTranslate2 com drivers CUDA desatualizados
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE = "int8"
WHISPER_LANGUAGE = "pt"

# Lazy loading: só carrega o modelo Whisper quando realmente precisar (grande redução de CPU no startup/idle)
LAZY_STT = os.getenv("LAZY_STT", "true").lower() == "true"

# ===== PyTorch Threading Constraints =====
torch.set_num_threads(CPU_THREADS)
torch.set_num_interop_threads(max(1, CPU_THREADS // 2))

# ===== Memory =====
# Banco de dados SQLite para persistência
KURI_DB = "kuri_memory.db"
MAX_MEMORY_MESSAGES = 50
CONTEXT_WINDOW = 20  # últimas N mensagens enviadas para o LLM

# ===== Background Tasks (Fase 4 + otimização CPU) =====
# Intervalos em número de mensagens. Aumente para reduzir uso de CPU/Grok API
RESUMO_INTERVALO = int(os.getenv("RESUMO_INTERVALO", "30"))
INSIGHTS_INTERVALO = int(os.getenv("INSIGHTS_INTERVALO", "40"))
AUTO_AVALIACAO_INTERVALO = int(os.getenv("AUTO_AVALIACAO_INTERVALO", "70"))

# ===== Prompt =====
PROMPT_FILE = get_resource_path("prompt_kuri.txt")

# ===== System =====
SILENCE_TIMEOUT = 8.0  # segundos de silêncio antes de "dormir"

# ===== Sleep / Modo Suspenso (baixo consumo) =====
SLEEP_TIMEOUT_MINUTES = int(os.getenv("SLEEP_TIMEOUT_MINUTES", "5"))  # inatividade para entrar em sono
SLEEP_WAKE_PHRASES = [
    "acorda kuri", "kuri acorda", "acorda", "ei kuri", "kuri ei", 
    "acorde", "volta", "está aí", "oi kuri"
]  # frases para acordar do modo sono (case insensitive)

# ===== Mic verification and sleep suspension =====
MAX_MIC_VERIFICATION_ATTEMPTS = 12   # after this many failed/no-input checks, suspend heavy listening
MAX_CONSECUTIVE_SILENCE = 25         # max silent loops before forcing sleep mode
SLEEP_LISTEN_INTERVAL = 8.0          # seconds between checks when in sleep (to reduce CPU)

# Depois que a conversa começa, ela escuta sem exigir o nome de novo.
CONVERSATION_WINDOW_SECONDS = int(os.getenv("CONVERSATION_WINDOW_SECONDS", "90"))
