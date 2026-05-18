import numpy as np
import sounddevice as sd
import tempfile
import wave
import os
import threading
import torch
from config import (
    WHISPER_MODEL,
    WHISPER_DEVICE,
    WHISPER_COMPUTE,
    WHISPER_LANGUAGE,
    CPU_THREADS,
)
from logger import get_logger

log = get_logger("stt")

# Carregamento do modelo Whisper
_model = None
_model_lock = threading.Lock()

# Carregamento do modelo Silero VAD
_vad_model = None
_vad_lock = threading.Lock()

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"

# Parâmetros otimizados de detecção
SILENCE_THRESHOLD = 60  # Fallback fixo
SILENCE_DURATION = 1.0  # Resposta mais rápida (corta após 1s de silêncio)
MAX_RECORD_SECONDS = 30  # Limite máximo

DYNAMIC_THRESHOLD = SILENCE_THRESHOLD


def _get_model():
    """Carrega o modelo de forma thread-safe."""
    global _model
    with _model_lock:
        if _model is None:
            log.info(
                f"Inicializando motor de voz Whisper ({WHISPER_MODEL}) no {WHISPER_DEVICE}..."
            )
            from faster_whisper import WhisperModel

            _model = WhisperModel(
                WHISPER_MODEL,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE,
                cpu_threads=CPU_THREADS,
            )
            log.info(
                f"Motor Whisper pronto! (Threads: {CPU_THREADS}, Compute: {WHISPER_COMPUTE})"
            )
    return _model

def _get_vad_model():
    """Carrega o modelo Silero VAD de forma thread-safe."""
    global _vad_model
    with _vad_lock:
        if _vad_model is None:
            log.info("Inicializando filtro de voz inteligente (Silero VAD)...")
            try:
                # Carrega silenciosamente o VAD local
                _vad_model, _ = torch.hub.load(
                    repo_or_dir='snakers4/silero-vad', 
                    model='silero_vad',
                    trust_repo=True
                )
                log.info("Silero VAD carregado com sucesso!")
            except Exception as e:
                log.error(f"Erro ao carregar Silero VAD: {e}")
    return _vad_model


# Pré-carrega os modelos em background ao importar o módulo
threading.Thread(target=_get_model, daemon=True, name="STTPreloader").start()
threading.Thread(target=_get_vad_model, daemon=True, name="VADPreloader").start()


def _get_input_device_idx() -> int:
    """Retorna o índice do dispositivo de gravação (prioriza Bluetooth/Headsets)."""
    try:
        devices = sd.query_devices()
        keywords = ["jbl", "headset", "bluetooth", "hands-free"]
        
        # 1. Tenta Bluetooth / Headsets
        for i, d in enumerate(devices):
            if d["max_input_channels"] > 0:
                if any(k in d["name"].lower() for k in keywords):
                    log.info(f"Microfone Bluetooth/Headset selecionado: {d['name']} (ID {i})")
                    return i
                    
        # 2. Tenta Padrão do Sistema
        default_idx = sd.default.device[0]
        if default_idx != -1:
            return default_idx
            
        # 3. Fallback para o primeiro válido
        for i, d in enumerate(devices):
            if d["max_input_channels"] > 0:
                return i
    except Exception as e:
        log.error(f"Erro ao buscar dispositivos de áudio: {e}")
        
    return sd.default.device[0]


async def calibrar_microfone(duration=2.0):
    """Grava o som ambiente por X segundos e define o threshold ideal."""
    global DYNAMIC_THRESHOLD
    log.info(f"Calibrando microfone por {duration}s...")

    device_idx = _get_input_device_idx()
    if device_idx == -1:
        return

    try:
        # Grava o áudio
        sd.rec(
            int(duration * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
        )
        sd.wait()
        log.info("Calibração concluída. (Amplitude descartada, VAD neural ativo!)")
    except Exception as e:
        log.error(f"Calibração falhou: {e}")


def gravar_audio() -> str | None:
    """Grava áudio do microfone até detectar silêncio usando Silero VAD. Retorna path do arquivo WAV."""
    frames = []
    silent_chunks = 0
    # Silero VAD funciona perfeitamente com chunks de 512 samples a 16kHz (32ms)
    chunk_size = 512
    chunk_duration = chunk_size / SAMPLE_RATE
    max_chunks = int(MAX_RECORD_SECONDS / chunk_duration)
    silence_chunks_needed = int(SILENCE_DURATION / chunk_duration)
    started_speaking = False

    device_idx = _get_input_device_idx()
    if device_idx == -1:
        log.error("Nenhum dispositivo de microfone válido encontrado!")
        return None

    vad_model = _get_vad_model()

    try:
        try:
            stream = sd.InputStream(
                device=device_idx,
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=DTYPE,
                blocksize=chunk_size,
            )
            stream.start()
        except Exception:
            # Fallback para 2 canais
            log.debug(f"Tentando device {device_idx} com 2 canais...")
            stream = sd.InputStream(
                device=device_idx,
                samplerate=SAMPLE_RATE,
                channels=2,
                dtype=DTYPE,
                blocksize=chunk_size,
            )
            stream.start()

        for _ in range(max_chunks):
            data, _ = stream.read(chunk_size)

            # Se tiver mais de 1 canal, pega apenas o primeiro
            if data.ndim > 1 and data.shape[1] > 1:
                data_proc = data[:, 0]
            else:
                data_proc = data.flatten()

            # Converter de int16 para float32 no range [-1.0, 1.0] para o VAD
            data_float = data_proc.astype(np.float32) / 32768.0
            
            is_speech = False
            if vad_model is not None:
                tensor_chunk = torch.from_numpy(data_float)
                prob = vad_model(tensor_chunk, SAMPLE_RATE).item()
                is_speech = prob > 0.5
            else:
                # Fallback de amplitude se VAD falhar em carregar
                amplitude = np.abs(data_proc).mean()
                is_speech = amplitude > DYNAMIC_THRESHOLD

            if is_speech:
                started_speaking = True
                silent_chunks = 0
                frames.append(data_proc.copy())
            elif started_speaking:
                silent_chunks += 1
                frames.append(data_proc.copy())
                if silent_chunks >= silence_chunks_needed:
                    break

        stream.stop()
        stream.close()

    except Exception as e:
        log.error(f"Gravação: {e}")
        return None

    if not frames or not started_speaking:
        return None

    # Salva em WAV temporário na pasta raiz
    audio_data = np.concatenate(frames)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir=".")
    tmp_path = tmp.name
    tmp.close()

    with wave.open(tmp_path, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_data.tobytes())

    return tmp_path


def transcrever(audio_path: str) -> str:
    """Transcreve áudio com filtro VAD ativado para maior precisão."""
    model = _get_model()
    try:
        segments, _ = model.transcribe(
            audio_path,
            language=WHISPER_LANGUAGE,
            beam_size=5,  # Aumentado de 1 para 5 para maior precisão (busca em feixe)
            vad_filter=True,  # Pula ruídos e foca na fala
            vad_parameters=dict(min_silence_duration_ms=500),
            initial_prompt="Isso é uma conversa com a Kuri, uma assistente pessoal sarcástica e gamer em português.",  # Ajuda no contexto e pontuação
        )
        return " ".join([s.text for s in segments]).strip()
    except Exception as e:
        log.error(f"Transcrição: {e}")
        return ""
    finally:
        try:
            os.remove(audio_path)
        except OSError:
            pass


def ouvir() -> str:
    """Função principal de entrada de voz."""
    audio_path = gravar_audio()
    if not audio_path:
        return ""
    return transcrever(audio_path)
