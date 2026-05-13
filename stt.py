import numpy as np
import sounddevice as sd
import tempfile
import wave
import os
import threading
from config import WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE, WHISPER_LANGUAGE

# Carregamento do modelo
_model = None
_model_lock = threading.Lock()

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"

# Parâmetros otimizados de detecção
SILENCE_THRESHOLD = 60        # Mais sensível para ouvir vozes mais baixas
SILENCE_DURATION = 1.0        # Resposta mais rápida (corta após 1s de silêncio)
MAX_RECORD_SECONDS = 30       # Limite máximo


def _get_model():
    """Carrega o modelo de forma thread-safe."""
    global _model
    with _model_lock:
        if _model is None:
            print(f"[STT] Inicializando motor de voz Whisper ({WHISPER_MODEL})...")
            from faster_whisper import WhisperModel
            _model = WhisperModel(
                WHISPER_MODEL,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE,
                cpu_threads=4  # Otimizado para CPU multi-core
            )
            print("[STT] Motor Whisper pronto e pré-carregado!")
    return _model


# Pré-carrega o modelo em background ao importar o módulo
threading.Thread(target=_get_model, daemon=True, name="STTPreloader").start()


def gravar_audio() -> str | None:
    """Grava áudio do microfone até detectar silêncio. Retorna path do arquivo WAV."""
    frames = []
    silent_chunks = 0
    chunk_duration = 0.1  # 100ms por chunk
    chunk_size = int(SAMPLE_RATE * chunk_duration)
    max_chunks = int(MAX_RECORD_SECONDS / chunk_duration)
    silence_chunks_needed = int(SILENCE_DURATION / chunk_duration)
    started_speaking = False

    try:
        stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE, blocksize=chunk_size)
        stream.start()

        for _ in range(max_chunks):
            data, _ = stream.read(chunk_size)
            amplitude = np.abs(data).mean()

            if amplitude > SILENCE_THRESHOLD:
                started_speaking = True
                silent_chunks = 0
                frames.append(data.copy())
            elif started_speaking:
                silent_chunks += 1
                frames.append(data.copy())
                if silent_chunks >= silence_chunks_needed:
                    break

        stream.stop()
        stream.close()

    except Exception as e:
        print(f"[ERRO] Gravação: {e}")
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
            beam_size=1,
            vad_filter=True,  # Pula ruídos e foca na fala
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        return " ".join([s.text for s in segments]).strip()
    except Exception as e:
        print(f"[ERRO] Transcrição: {e}")
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
