import numpy as np
import sounddevice as sd
import tempfile
import wave
import os
import threading
from config import (
    WHISPER_MODEL,
    WHISPER_DEVICE,
    WHISPER_COMPUTE,
    WHISPER_LANGUAGE,
    CPU_THREADS,
)
from logger import get_logger

log = get_logger("stt")

# Carregamento do modelo
_model = None
_model_lock = threading.Lock()

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


# Pré-carrega o modelo em background ao importar o módulo
threading.Thread(target=_get_model, daemon=True, name="STTPreloader").start()


async def calibrar_microfone(duration=2.0):
    """Grava o som ambiente por X segundos e define o threshold ideal."""
    global DYNAMIC_THRESHOLD
    log.info(f"Calibrando microfone por {duration}s...")

    device_idx = sd.default.device[0]
    if device_idx == -1:
        return

    try:
        # Grava o áudio
        audio = sd.rec(
            int(duration * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
        )
        sd.wait()

        # Calcula a média da amplitude
        amplitude_media = np.abs(audio).mean()
        # Define threshold como a média + margem de segurança (multiplicador)
        # Se for muito baixo (silêncio absoluto), usa o fallback de 60
        DYNAMIC_THRESHOLD = max(SILENCE_THRESHOLD, int(amplitude_media * 1.8))
        log.info(f"Calibração concluída. Novo SILENCE_THRESHOLD: {DYNAMIC_THRESHOLD}")
    except Exception as e:
        log.error(f"Calibração falhou: {e}")
        DYNAMIC_THRESHOLD = SILENCE_THRESHOLD


def gravar_audio() -> str | None:
    """Grava áudio do microfone até detectar silêncio. Retorna path do arquivo WAV."""
    frames = []
    silent_chunks = 0
    chunk_duration = 0.1  # 100ms por chunk
    chunk_size = int(SAMPLE_RATE * chunk_duration)
    max_chunks = int(MAX_RECORD_SECONDS / chunk_duration)
    silence_chunks_needed = int(SILENCE_DURATION / chunk_duration)
    started_speaking = False

    # Verifica se há um device padrão válido, senão procura o primeiro disponível
    device_idx = sd.default.device[0]
    if device_idx == -1:
        devices = sd.query_devices()
        for i, d in enumerate(devices):
            if d["max_input_channels"] > 0:
                device_idx = i
                break

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

            amplitude = np.abs(data_proc).mean()

            if amplitude > DYNAMIC_THRESHOLD:
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
