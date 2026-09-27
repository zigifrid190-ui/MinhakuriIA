"""
ollama_fallback.py

Extraído durante aprofundamento da Fase 1 - Estabilização.

Lógica de fallback para Ollama local quando a API principal (Grok) falha.
"""

import time

import httpx

from config import (
    OLLAMA_ENABLED,
    OLLAMA_URL,
    OLLAMA_MODEL,
    OLLAMA_API_URL,
    GROK_TEMPERATURE,
)
from logger import get_logger
from prompt_builder import _build_system_prompt, _build_messages, _calcular_max_tokens
from memory import adicionar_interacao

log = get_logger("ollama_fallback")

# ===== Ollama Status Tracking =====
_ollama_available = None
_ollama_last_check = 0
_OLLAMA_CHECK_INTERVAL = 60.0


async def verificar_ollama() -> bool:
    """Verifica se o Ollama está rodando localmente. Cacheia resultado por 60s."""
    global _ollama_available, _ollama_last_check

    if not OLLAMA_ENABLED:
        return False

    now = time.monotonic()
    if _ollama_available is not None and (now - _ollama_last_check) < _OLLAMA_CHECK_INTERVAL:
        return _ollama_available

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            _ollama_available = resp.status_code == 200
            if _ollama_available:
                models = [m["name"] for m in resp.json().get("models", [])]
                log.info(f"Ollama online! Modelos disponíveis: {models}")
    except Exception:
        _ollama_available = False

    _ollama_last_check = now
    return _ollama_available


async def tentar_ollama_fallback(texto: str, historico: list, base_prompt: str, emotional_context: str) -> dict | None:
    """Tenta responder usando Ollama local como fallback."""
    if not await verificar_ollama():
        log.warning("Ollama não disponível para fallback.")
        return None

    log.info(f"Ativando fallback Ollama ({OLLAMA_MODEL})...")

    system_prompt = _build_system_prompt(
        texto,
        base_prompt,
        emotional_context,
    )
    messages = _build_messages(texto, historico, system_prompt)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                OLLAMA_API_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "temperature": GROK_TEMPERATURE,
                    "max_tokens": _calcular_max_tokens(texto),
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()
            resposta = data.get("message", {}).get("content") or data.get("choices", [{}])[0].get("message", {}).get("content", "")
            resposta = resposta.strip()

            import re
            emocao = "neutral"
            match = re.match(r"^\[(.*?)\]\s*(.*)", resposta, flags=re.DOTALL)
            if match:
                emoc_tag = match.group(1).lower().strip()
                if emoc_tag in ["neutral", "cool", "surprised", "blushing", "angry"]:
                    emocao = emoc_tag
                resposta = match.group(2).strip()

            adicionar_interacao(historico, texto, resposta)
            log.info("Resposta via Ollama concluída com sucesso!")
            return {"resposta": resposta, "acao_executada": None, "emocao": emocao}

    except Exception as e:
        log.error(f"Fallback Ollama falhou: {e}")
        return None
