import numpy as np
import sounddevice as sd
import tempfile
import wave
import os
import threading
import torch
import queue
import time
from config import (
    WHISPER_MODEL,
    WHISPER_DEVICE,
    WHISPER_COMPUTE,
    WHISPER_LANGUAGE,
    CPU_THREADS,
    LAZY_STT,
)
from logger import get_logger
from path_utils import get_resource_path

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
MAX_RECORD_SECONDS = 30  # Limite máximo se já detectou fala
NO_SPEECH_SECONDS = 8.0  # Se ninguém falou, não prende o mic por 30s

DYNAMIC_THRESHOLD = SILENCE_THRESHOLD


def _get_model():
    """Carrega o modelo de forma thread-safe. Suporta lazy loading (LAZY_STT)."""
    global _model
    with _model_lock:
        if _model is None:
            if LAZY_STT:
                log.info(f"Lazy STT ativado. Modelo Whisper será carregado na primeira vez que precisar ouvir.")
            else:
                log.info(
                    f"Inicializando motor de voz Whisper ({WHISPER_MODEL}) no {WHISPER_DEVICE}..."
                )
            from faster_whisper import WhisperModel

            # Tenta carregar do diretório local bundled primeiro
            local_model_dir = get_resource_path(os.path.join("models", f"whisper-{WHISPER_MODEL}"))
            if os.path.isdir(local_model_dir) and os.path.exists(os.path.join(local_model_dir, "model.bin")):
                model_path = local_model_dir
                log.info(f"Carregando Whisper do bundle local: {model_path}")
            else:
                model_path = WHISPER_MODEL  # Fallback: baixa do HuggingFace
                log.info(f"Bundle local não encontrado, baixando modelo '{WHISPER_MODEL}'...")

            try:
                _model = WhisperModel(
                    model_path,
                    device=WHISPER_DEVICE,
                    compute_type=WHISPER_COMPUTE,
                    cpu_threads=CPU_THREADS,
                )
                log.info(
                    f"Motor Whisper pronto! (Threads: {CPU_THREADS}, Device: {WHISPER_DEVICE}, Compute: {WHISPER_COMPUTE}, Lazy: {LAZY_STT})"
                )
            except Exception as e:
                if WHISPER_DEVICE == "cuda":
                    log.warning(f"Falha ao carregar Whisper no CUDA ({e}). Ativando fallback para CPU (int8)...")
                    _model = WhisperModel(
                        model_path,
                        device="cpu",
                        compute_type="int8",
                        cpu_threads=CPU_THREADS,
                    )
                    log.info(
                        f"Motor Whisper pronto em modo fallback! (Threads: {CPU_THREADS}, Device: cpu, Compute: int8)"
                    )
                else:
                    raise e
    return _model

def _get_vad_model():
    """Carrega o modelo Silero VAD de forma thread-safe."""
    global _vad_model
    with _vad_lock:
        if _vad_model is None:
            log.info("Inicializando filtro de voz inteligente (Silero VAD)...")
            try:
                # Tenta carregar do JIT local bundled primeiro
                local_vad_path = get_resource_path(os.path.join("models", "silero-vad", "silero_vad.jit"))
                if os.path.isfile(local_vad_path):
                    log.info(f"Carregando Silero VAD do bundle local: {local_vad_path}")
                    _vad_model = torch.jit.load(local_vad_path, map_location=torch.device('cpu'))
                    _vad_model.eval()
                else:
                    # Fallback: baixa do torch.hub
                    log.info("Bundle local do VAD não encontrado, baixando...")
                    _vad_model, _ = torch.hub.load(
                        repo_or_dir='snakers4/silero-vad',
                        model='silero_vad',
                        trust_repo=True
                    )
                log.info("Silero VAD carregado com sucesso!")
            except Exception as e:
                log.error(f"Erro ao carregar Silero VAD: {e}")
    return _vad_model


# Os modelos Whisper e Silero VAD serão carregados de forma síncrona e thread-safe sob demanda no primeiro uso do áudio.


# Fila para transferir chunks de áudio do callback para a thread principal
_audio_queue = queue.Queue()

def _audio_callback(indata, frames, time, status):
    if status:
        log.warning(f"Status do áudio no callback: {status}")
    _audio_queue.put(indata.copy())

_device_cache = None
_device_cache_time = 0.0
_DEVICE_CACHE_TTL = 30.0  # segundos

def _get_working_input_device() -> tuple[int | None, int, int]:
    """Retorna o índice, sample rate e canais usando um cache com TTL de 30 segundos."""
    global _device_cache, _device_cache_time
    now = time.time()
    if _device_cache is not None and (now - _device_cache_time) < _DEVICE_CACHE_TTL:
        return _device_cache

    result = _get_working_input_device_uncached()
    _device_cache = result
    _device_cache_time = now
    return result

def _get_working_input_device_uncached() -> tuple[int | None, int, int]:
    """Retorna o índice, sample rate e canais do primeiro dispositivo de entrada funcional."""
    try:
        devices = sd.query_devices()
    except Exception as e:
        log.error(f"Erro ao listar dispositivos com sounddevice: {e}")
        return None, 16000, 1

    # 1. Tenta usar o dispositivo padrão configurado no sounddevice primeiro
    default_input_idx = sd.default.device[0]
    if default_input_idx is not None and default_input_idx >= 0 and default_input_idx < len(devices):
        d = devices[default_input_idx]
        if d.get("max_input_channels", 0) > 0:
            native_sr = int(d.get("default_samplerate", 16000))
            native_channels = int(d.get("max_input_channels", 1))
            try:
                test_stream = sd.InputStream(
                    device=default_input_idx,
                    samplerate=native_sr,
                    channels=native_channels,
                    dtype=DTYPE,
                    callback=lambda *args: None
                )
                with test_stream:
                    pass
                log.info(f"Usando dispositivo configurado: {d['name']} (ID {default_input_idx}) | Config nativa: {native_sr}Hz, {native_channels} canais")
                return default_input_idx, native_sr, native_channels
            except Exception as e:
                log.debug(f"Falha ao abrir dispositivo configurado {d['name']} (ID {default_input_idx}): {e}")

    keywords = ["jbl", "headset", "bluetooth", "hands-free", "kon", "eg 350"]
    
    # 2. Filtra dispositivos de entrada válidos
    input_devices = []
    for i, d in enumerate(devices):
        if d.get("max_input_channels", 0) > 0:
            input_devices.append((i, d))

    if not input_devices:
        return None, 16000, 1

    # 3. Ordena priorizando Bluetooth/Headsets
    def get_priority(item):
        name = item[1]["name"].lower()
        if any(k in name for k in keywords):
            return 0  # Alta prioridade
        return 1  # Baixa prioridade

    input_devices.sort(key=get_priority)

    # 4. Varre os candidatos tentando abrir um stream nativo curto para verificar se funciona
    for idx, d in input_devices:
        native_sr = int(d.get("default_samplerate", 16000))
        native_channels = int(d.get("max_input_channels", 1))
        
        try:
            # Tenta abrir um stream de teste não bloqueante usando um callback vazio
            test_stream = sd.InputStream(
                device=idx,
                samplerate=native_sr,
                channels=native_channels,
                dtype=DTYPE,
                callback=lambda *args: None
            )
            with test_stream:
                pass
            log.info(f"Dispositivo selecionado via fallback: {d['name']} (ID {idx}) | Config nativa: {native_sr}Hz, {native_channels} canais")
            return idx, native_sr, native_channels
        except Exception as e:
            log.debug(f"Falha ao testar dispositivo {d['name']} (ID {idx}): {e}")

    # Fallback final para o default absoluto do sistema
    default_idx = sd.default.device[0]
    if default_idx is not None and default_idx != -1:
        try:
            d = devices[default_idx]
            return default_idx, int(d.get("default_samplerate", 16000)), int(d.get("max_input_channels", 1))
        except Exception:
            pass

    return None, 16000, 1


async def calibrar_microfone(duration=2.0):
    """Grava o som ambiente por X segundos e define o threshold ideal."""
    global DYNAMIC_THRESHOLD
    log.info(f"Calibrando microfone por {duration}s...")

    device_idx, native_sr, native_channels = _get_working_input_device()
    if device_idx is None:
        log.warning("Calibração cancelada: nenhum microfone funcional respondendo.")
        return

    # Fila temporária local para a calibração
    calib_queue = queue.Queue()
    def calib_callback(indata, frames, time, status):
        calib_queue.put(indata.copy())

    try:
        stream = sd.InputStream(
            device=device_idx,
            samplerate=native_sr,
            channels=native_channels,
            dtype=DTYPE,
            callback=calib_callback
        )
        
        frames = []
        with stream:
            num_samples_needed = int(duration * native_sr)
            samples_captured = 0
            while samples_captured < num_samples_needed:
                try:
                    chunk = calib_queue.get(timeout=0.5)
                    if chunk.ndim > 1 and chunk.shape[1] > 1:
                        chunk_mono = chunk[:, 0]
                    else:
                        chunk_mono = chunk.flatten()
                    frames.append(chunk_mono)
                    samples_captured += len(chunk_mono)
                except queue.Empty:
                    break

        if not frames:
            return

        audio = np.concatenate(frames)
        audio_flat = audio.flatten()
        noise_mean = np.abs(audio_flat).mean()
        noise_std = np.std(audio_flat)
        
        DYNAMIC_THRESHOLD = max(SILENCE_THRESHOLD, int(noise_mean + 3.0 * noise_std))
        log.info(f"Calibração concluída! Ruído médio: {noise_mean:.1f}, Threshold de fallback ajustado para: {DYNAMIC_THRESHOLD} (VAD neural ativo se carregado)")
    except Exception as e:
        log.error(f"Calibração falhou: {e}")


def gravar_audio() -> str | None:
    """Grava áudio do microfone até detectar silêncio usando Silero VAD e resampling nativo."""
    try:
        from kuri_runtime import is_kuri_speaking
        if is_kuri_speaking():
            log.debug("Mic ignorado: Kuri ainda está falando (anti-eco).")
            return None
    except Exception:
        pass

    device_idx, native_sr, native_channels = _get_working_input_device()
    if device_idx is None:
        log.error("Nenhum dispositivo de gravação ativo/funcional encontrado!")
        return None

    # Esvazia a fila global
    while not _audio_queue.empty():
        try:
            _audio_queue.get_nowait()
        except queue.Empty:
            break

    try:
        stream = sd.InputStream(
            device=device_idx,
            samplerate=native_sr,
            channels=native_channels,
            dtype=DTYPE,
            callback=_audio_callback
        )
    except Exception as e:
        log.error(f"Erro ao abrir InputStream no device {device_idx}: {e}")
        return None

    frames_16k = []
    vad_buffer = np.array([], dtype=np.float32)
    started_speaking = False
    silent_chunks = 0
    
    chunk_size_16k = 512
    chunk_duration_16k = chunk_size_16k / 16000.0  # 32ms
    silence_chunks_needed = int(SILENCE_DURATION / chunk_duration_16k)
    max_chunks = int(MAX_RECORD_SECONDS / chunk_duration_16k)
    chunks_processed = 0

    vad_model = _get_vad_model()
    _vad_tensor = torch.zeros(chunk_size_16k, dtype=torch.float32)

    try:
        with torch.inference_mode(), stream:
            while chunks_processed < max_chunks:
                try:
                    # Aguarda até 1s por novos dados do callback
                    chunk = _audio_queue.get(timeout=1.0)
                except queue.Empty:
                    log.warning("Timeout aguardando dados de áudio do callback.")
                    break

                # Headset estéreo: mistura os canais. Canal 0 só deixa a Kuri surda
                # se o microfone vier no direito.
                if chunk.ndim > 1 and chunk.shape[1] > 1:
                    chunk_mono = chunk.mean(axis=1)
                else:
                    chunk_mono = chunk.flatten()

                # Normaliza para float32 no range [-1.0, 1.0] para VAD e interpolação
                chunk_float = chunk_mono.astype(np.float32) / 32768.0

                # Resample linear usando np.interp
                if native_sr != 16000:
                    duration = len(chunk_float) / native_sr
                    num_target_samples = int(duration * 16000)
                    if num_target_samples > 0:
                        src_indices = np.linspace(0, len(chunk_float) - 1, num_target_samples)
                        chunk_resampled = np.interp(src_indices, np.arange(len(chunk_float)), chunk_float)
                    else:
                        chunk_resampled = np.array([], dtype=np.float32)
                else:
                    chunk_resampled = chunk_float

                # Acumula no buffer VAD
                vad_buffer = np.concatenate((vad_buffer, chunk_resampled))

                # Processa blocos de 512 amostras a 16000Hz (32ms)
                while len(vad_buffer) >= chunk_size_16k:
                    vad_chunk = vad_buffer[:chunk_size_16k]
                    vad_buffer = vad_buffer[chunk_size_16k:]

                    is_speech = False
                    if vad_model is not None:
                        try:
                            _vad_tensor.copy_(torch.from_numpy(vad_chunk))
                            prob = vad_model(_vad_tensor, 16000).item()
                            is_speech = prob > 0.5
                        except Exception as e:
                            # Evita inundar o log com erros repetitivos em cada chunk de 32ms
                            static_logged = getattr(_get_working_input_device, "_logged_vad_error", False)
                            if not static_logged:
                                log.warning(f"Silero VAD encontrou um erro ({e}). Ativando fallback de amplitude automática.")
                                _get_working_input_device._logged_vad_error = True
                            
                            amplitude = np.abs(vad_chunk).mean() * 32768.0
                            is_speech = amplitude > DYNAMIC_THRESHOLD
                    else:
                        amplitude = np.abs(vad_chunk).mean() * 32768.0
                        is_speech = amplitude > DYNAMIC_THRESHOLD

                    chunk_int16 = (vad_chunk * 32768.0).astype(np.int16)

                    if is_speech:
                        started_speaking = True
                        silent_chunks = 0
                        frames_16k.append(chunk_int16)
                    elif started_speaking:
                        silent_chunks += 1
                        frames_16k.append(chunk_int16)
                        if silent_chunks >= silence_chunks_needed:
                            # Silêncio detectado após a fala, encerra gravação
                            chunks_processed = max_chunks
                            break

                    chunks_processed += 1
                    if chunks_processed >= max_chunks:
                        break
                    if (
                        not started_speaking
                        and (chunks_processed * chunk_duration_16k) >= NO_SPEECH_SECONDS
                    ):
                        break

    except Exception as e:
        log.error(f"Erro no loop de gravação: {e}")
        return None

    if not frames_16k or not started_speaking:
        return None

    # Salva arquivo final WAV de 1 canal a 16000Hz
    audio_data = np.concatenate(frames_16k)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir=tempfile.gettempdir())
    tmp_path = tmp.name
    tmp.close()

    try:
        with wave.open(tmp_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(audio_data.tobytes())
        return tmp_path
    except Exception as e:
        log.error(f"Erro ao salvar arquivo WAV: {e}")
        return None


def transcrever(audio_path: str) -> str:
    """Transcreve áudio com filtro VAD ativado para maior precisão."""
    model = _get_model()
    try:
        segments, _ = model.transcribe(
            audio_path,
            language=WHISPER_LANGUAGE,
            beam_size=1,  # beam=1 (greedy) é ~5x mais rápido; suficiente para comandos de voz curtos
            vad_filter=True,  # Pula ruídos e foca na fala
            vad_parameters=dict(min_silence_duration_ms=500),
            initial_prompt="Isso é uma conversa informal com a Kuri (ou Curi), uma assistente pessoal sarcástica, programadora e gamer em português. Comandos comuns: Kuri, abre o Chrome, Spotify, Discord, VS Code, git status, commits, repositório, Python, Windows, Grok. Use gírias e pontuação correta.",  # Ajuda no contexto e pontuação
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


def is_microphone_available() -> bool:
    """Retorna True se houver pelo menos um dispositivo de entrada de áudio funcional."""
    idx, _, _ = _get_working_input_device()
    return idx is not None
