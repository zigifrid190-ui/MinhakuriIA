"""
Runtime único da Kuri.

CLI (`main.py`) e desktop (`gui/kuri_core.py`) usam o mesmo caminho:
atenção (wake word + janela de conversa) → pensar_stream → TTS.
"""

from __future__ import annotations

import re
import threading
import time
from typing import Any, AsyncIterator, Callable, Optional

from config import CONVERSATION_WINDOW_SECONDS, SLEEP_WAKE_PHRASES
from logger import get_logger

log = get_logger("runtime")

_conversation_until = 0.0
_speaking = threading.Event()
_speak_tail_until = 0.0
_SPEAK_TAIL_SECONDS = 0.35

ChunkHook = Callable[[dict], None]


def is_wake_word(texto: str) -> bool:
    """True se o texto chama a Kuri ou pede para acordar."""
    if not texto:
        return False
    texto_limpo = re.sub(r"[^a-z0-9\s]", "", texto.lower().strip())
    for frase in SLEEP_WAKE_PHRASES:
        if frase in texto_limpo:
            return True
    palavras = texto_limpo.split()
    if palavras and any(w in ("kuri", "curi", "curie") for w in palavras[:8]):
        return True
    if "kuri" in texto_limpo or " curi " in f" {texto_limpo} ":
        return True
    return False


def open_conversation() -> None:
    global _conversation_until
    _conversation_until = time.time() + CONVERSATION_WINDOW_SECONDS


def conversation_open() -> bool:
    return time.time() < _conversation_until


def set_speaking(on: bool) -> None:
    """Marca que a Kuri está (ou acabou de) falar — o mic não deve se ouvir."""
    global _speak_tail_until
    if on:
        _speaking.set()
    else:
        _speaking.clear()
        _speak_tail_until = time.time() + _SPEAK_TAIL_SECONDS


def is_kuri_speaking() -> bool:
    return _speaking.is_set() or time.time() < _speak_tail_until


async def _with_chunk_hook(
    stream_gen: AsyncIterator[dict],
    hook: Optional[ChunkHook],
) -> AsyncIterator[dict]:
    async for chunk in stream_gen:
        if hook:
            try:
                hook(chunk)
            except Exception as e:
                log.warning(f"chunk_hook: {e}")
        yield chunk


async def process_utterance(
    texto: str,
    *,
    premium: bool | None = None,
    chunk_hook: Optional[ChunkHook] = None,
) -> dict[str, Any]:
    """
    Caminho único: LLM (com tools no stream) + fala.
    Usado pelo widget e pelo CLI.
    """
    from brain import pensar_stream
    from tts import falar_stream

    stream_gen = _with_chunk_hook(pensar_stream(texto), chunk_hook)
    resultado = await falar_stream(stream_gen, premium=premium)
    open_conversation()
    return resultado
