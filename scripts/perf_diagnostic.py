"""
Diagnóstico de performance da Kuri — mede latência de cada etapa do pipeline.
Roda sem precisar de microfone (simula inputs).
"""
import asyncio
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def main():
    print("=" * 60)
    print("🔬 KURI PERFORMANCE DIAGNOSTIC")
    print("=" * 60)

    # 1. Medir tempo de import dos módulos
    t0 = time.perf_counter()
    from config import GROK_MODEL, OLLAMA_ENABLED, OLLAMA_MODEL
    t_config = time.perf_counter() - t0
    print(f"\n📦 Config import:        {t_config*1000:.0f}ms")

    t0 = time.perf_counter()
    from brain import _build_system_prompt, pensar, pensar_stream, verificar_ollama
    t_brain = time.perf_counter() - t0
    print(f"🧠 Brain import:         {t_brain*1000:.0f}ms")

    # 2. Medir system prompt (com 5 queries SQLite)
    t0 = time.perf_counter()
    prompt = _build_system_prompt("teste rápido")
    t_prompt = time.perf_counter() - t0
    print(f"\n📝 System prompt build:  {t_prompt*1000:.0f}ms")
    print(f"   Prompt size:          {len(prompt)} chars")

    # 3. Medir cache hit do system prompt (deve ser ~0ms)
    t0 = time.perf_counter()
    _build_system_prompt("teste rápido")
    t_cache = time.perf_counter() - t0
    print(f"💾 System prompt (cache): {t_cache*1000:.2f}ms")

    # 4. Verificar Ollama
    print(f"\n🦙 Ollama enabled:       {OLLAMA_ENABLED}")
    print(f"   Ollama model:         {OLLAMA_MODEL}")
    t0 = time.perf_counter()
    ollama_ok = await verificar_ollama()
    t_ollama = time.perf_counter() - t0
    print(f"   Ollama online:        {'✅ SIM' if ollama_ok else '❌ NÃO'} ({t_ollama*1000:.0f}ms)")

    # 5. Medir LLM (Grok API) com uma pergunta curta
    print(f"\n🌐 LLM Principal:        {GROK_MODEL}")
    print("   Testando resposta curta...")

    t0 = time.perf_counter()
    try:
        result = await pensar("Kuri, diz oi rápido")
        t_llm = time.perf_counter() - t0
        resposta = result.get("resposta", "")[:80]
        print(f"   Tempo total pensar(): {t_llm*1000:.0f}ms")
        print(f"   Resposta:             \"{resposta}\"")
    except Exception as e:
        t_llm = time.perf_counter() - t0
        print(f"   ERRO após {t_llm*1000:.0f}ms: {e}")

    # 6. Testar streaming
    print("\n🔄 Testando pensar_stream()...")
    t0 = time.perf_counter()
    t_first_chunk = None
    chunks = []
    try:
        async for chunk in pensar_stream("Kuri, me conta algo interessante"):
            if t_first_chunk is None:
                t_first_chunk = time.perf_counter() - t0
            chunks.append(chunk.get("sentenca", ""))
        t_total_stream = time.perf_counter() - t0
        print(f"   Tempo até 1ª sentença:  {t_first_chunk*1000:.0f}ms")
        print(f"   Tempo total stream:     {t_total_stream*1000:.0f}ms")
        print(f"   Chunks recebidos:       {len(chunks)}")
        if chunks:
            print(f"   1ª sentença:            \"{chunks[0][:60]}\"")
    except Exception as e:
        print(f"   ERRO no stream: {e}")

    # Resumo
    print("\n" + "=" * 60)
    print("📊 RESUMO")
    print("=" * 60)
    print(f"  Config+Brain import:     {(t_config+t_brain)*1000:.0f}ms")
    print(f"  System prompt (cold):    {t_prompt*1000:.0f}ms")
    print(f"  System prompt (cached):  {t_cache*1000:.2f}ms")
    print(f"  Ollama check:            {t_ollama*1000:.0f}ms")
    if t_first_chunk:
        print(f"  Stream 1st chunk:        {t_first_chunk*1000:.0f}ms  ← PERCEPÇÃO DO USUÁRIO")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
