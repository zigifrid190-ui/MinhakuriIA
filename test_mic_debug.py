"""
Diagnostico de microfone v3
"""

import sys
import io
import sounddevice as sd
import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 1. Lista dispositivos de input
print("=" * 60)
print("DISPOSITIVOS DE AUDIO (ENTRADA)")
print("=" * 60)
devices = sd.query_devices()
input_devices = []
for i, d in enumerate(devices):
    if d["max_input_channels"] > 0:
        input_devices.append(i)
        print(f"  [{i}] {d['name']}")

try:
    default_dev = sd.default.device
    if hasattr(default_dev, "input"):
        default_input = default_dev.input
    elif isinstance(default_dev, (list, tuple)):
        default_input = default_dev[0]
    else:
        default_input = int(default_dev)
    print(f"\n>>> Device de entrada padrao: [{default_input}]")
except Exception as e:
    print(f"\n>>> Nao consegui identificar o device padrao: {e}")
    default_input = input_devices[0] if input_devices else 0

print("=" * 60)

# 2. Grava 5 segundos e mostra amplitude em tempo real
SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"
DURATION = 5
CHUNK = 0.1

print(f"\nGravando {DURATION}s de audio...")
print("   FALE ALGO AGORA!\n")

try:
    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype=DTYPE,
        blocksize=int(SAMPLE_RATE * CHUNK),
    )
    stream.start()

    amplitudes = []
    for i in range(int(DURATION / CHUNK)):
        data, _ = stream.read(int(SAMPLE_RATE * CHUNK))
        amp = np.abs(data).mean()
        amplitudes.append(amp)
        bar_len = int(amp / 50)
        bar = "#" * min(bar_len, 60)
        print(f"  {i*0.1:4.1f}s | amp={amp:8.1f} | {bar}")

    stream.stop()
    stream.close()

    max_amp = max(amplitudes)
    avg_amp = np.mean(amplitudes)

    print("\n" + "=" * 60)
    print("RESULTADO")
    print("=" * 60)
    print(f"  Amplitude MAXIMA:  {max_amp:.1f}")
    print(f"  Amplitude MEDIA:   {avg_amp:.1f}")
    print("  Threshold no stt.py: 500")
    print()

    if max_amp < 10:
        print("  [X] Nenhum audio detectado!")
        print("     -> Microfone MUTADO ou device errado.")
        print("     -> Tente: Settings > Sound > Input > escolha o mic certo.")
    elif max_amp < 500:
        sugestao = max(int(max_amp * 0.3), 20)
        print("  [!] Audio detectado mas ABAIXO do threshold (500)!")
        print(f"     -> Amplitude maxima: {max_amp:.0f}")
        print(f"     -> SOLUCAO: Reduzir SILENCE_THRESHOLD no stt.py para ~{sugestao}")
    else:
        print("  [OK] Microfone funcionando bem!")

except Exception as e:
    print(f"ERRO ao gravar: {e}")
