import numpy as np
import sounddevice as sd
import tempfile
import wave
import os
from config import WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE, WHISPER_LANGUAGE

# Carregamento lazy do modelo (só inicializa na primeira chamada)
_model = None

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"

# Parâmetros de detecção de silêncio
SILENCE_THRESHOLD = 100       # amplitude mínima para considerar som (ajustado para headset BT)
SILENCE_DURATION = 1.5        # segundos de silêncio para parar de gravar
MAX_RECORD_SECONDS = 30       # limite máximo de gravação


def _get_model():
    global _model
    if _model is None:
        print(f"[BRAIN] Carregando modelo Whisper ({WHISPER_MODEL})... (primeira vez pode demorar)")
        from faster_whisper import WhisperModel
        _model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE)
        print("[OK] Modelo Whisper carregado!")
    return _model


def gravar_audio() -> str | None:
    """Grava áudio do microfone até detectar silêncio. Retorna path do arquivo WAV."""
    print("[MIC] Ouvindo... (fale agora)")

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
            # Se não começou a falar, descarta (não grava silêncio inicial)

        stream.stop()
        stream.close()

    except Exception as e:
        print(f"[ERRO] Erro na gravacao: {e}")
        return None

    if not frames or not started_speaking:
        return None

    # Salva em arquivo WAV temporário
    audio_data = np.concatenate(frames)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir=".")
    tmp_path = tmp.name
    tmp.close()

    with wave.open(tmp_path, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_data.tobytes())

    return tmp_path


def transcrever(audio_path: str) -> str:
    """Transcreve um arquivo de áudio para texto usando Whisper local."""
    model = _get_model()
    try:
        segments, info = model.transcribe(audio_path, language=WHISPER_LANGUAGE, beam_size=1)
        texto = " ".join([s.text for s in segments]).strip()
        return texto
    except Exception as e:
        print(f"[ERRO] Erro na transcricao: {e}")
        return ""
    finally:
        try:
            os.remove(audio_path)
        except OSError:
            pass


def ouvir() -> str:
    """Grava áudio do microfone e retorna o texto transcrito."""
    audio_path = gravar_audio()
    if not audio_path:
        return ""
    texto = transcrever(audio_path)
    return texto
