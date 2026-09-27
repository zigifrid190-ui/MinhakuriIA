"""
tool_orchestrator.py

Extraído durante conclusão da Fase 1 - Estabilização.

Responsável por orquestrar a execução de tool chains (múltiplas chamadas de ferramentas)
de forma segura e controlada.
"""

import asyncio
import json
from typing import Any, Dict, List

import httpx

from config import GROK_MODEL, GROK_TEMPERATURE, GROK_URL, GROK_API_KEY
from logger import get_logger
from actions import REGISTRY
from prompt_builder import _calcular_max_tokens

log = get_logger("tool_orchestrator")


MAX_TOOL_ITERATIONS = 5


async def executar_tool_chain(
    client: httpx.AsyncClient,
    initial_messages: List[Dict[str, Any]],
    texto: str,
    base_prompt: str,
    emotional_context: str,
    tools_schema: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Executa o loop de tool calling de forma controlada.

    Retorna um dict com:
    - "mensagens": lista final de mensagens
    - "acoes_executadas": lista de resultados das ações
    - "resposta_final": resposta textual se já disponível
    """
    messages = list(initial_messages)
    acoes_executadas: List[str] = []

    for iteration in range(MAX_TOOL_ITERATIONS):
        # Retry com backoff exponencial (Fase 2 - Confiabilidade)
        max_retries = 2
        response = None
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                response = await client.post(
                    GROK_URL,
                    headers={"Authorization": f"Bearer {GROK_API_KEY}"},
                    json={
                        "model": GROK_MODEL,
                        "messages": messages,
                        "temperature": GROK_TEMPERATURE,
                        "max_tokens": _calcular_max_tokens(texto) if iteration == 0 else 450,
                        "tools": tools_schema or [],
                        "tool_choice": "auto",
                    },
                )
                response.raise_for_status()
                break
            except Exception as e:
                last_error = e
                delay = 0.5 * (2 ** attempt)  # exponential backoff
                log.warning(f"Tentativa {attempt+1}/{max_retries+1} falhou: {e}. Aguardando {delay}s...")
                if attempt < max_retries:
                    await asyncio.sleep(delay)

        if response is None:
            raise last_error or Exception("Falha após retries no LLM")

        data = response.json()
        choice = data["choices"][0]
        message = choice["message"]

        if not message.get("tool_calls"):
            # Resposta final sem tools
            return {
                "mensagens": messages,
                "acoes_executadas": acoes_executadas,
                "resposta_final": message.get("content", "..."),
            }

        # Registra a mensagem com tool_calls
        messages.append(message)

        for tool_call in message["tool_calls"]:
            func_name = tool_call["function"]["name"]
            func_args = json.loads(tool_call["function"]["arguments"])

            log.info(f"Tool chain [{iteration+1}]: {func_name}({func_args})")

            if func_name in REGISTRY:
                try:
                    resultado = REGISTRY[func_name](**func_args)
                    log.info(f"Resultado: {resultado}")
                    acoes_executadas.append(str(resultado))
                except Exception as e:
                    resultado = f"Erro ao executar '{func_name}': {e}"
                    log.error(resultado)
                    acoes_executadas.append(resultado)
            else:
                resultado = f"Ação '{func_name}' não encontrada."
                acoes_executadas.append(resultado)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": str(resultado),
                }
            )

    # Se esgotou iterações, força uma resposta final
    log.warning(f"Tool chain atingiu o limite de {MAX_TOOL_ITERATIONS} iterações.")

    try:
        final = await client.post(
            GROK_URL,
            headers={"Authorization": f"Bearer {GROK_API_KEY}"},
            json={
                "model": GROK_MODEL,
                "messages": messages,
                "temperature": GROK_TEMPERATURE,
                "max_tokens": 450,
            },
        )
        final.raise_for_status()
        resposta = final.json()["choices"][0]["message"]["content"]
    except Exception as e:
        log.warning(f"Falha ao forçar resposta final: {e}")
        resposta = f"[cool] Executei {len(acoes_executadas)} ação(ões), velho."

    return {
        "mensagens": messages,
        "acoes_executadas": acoes_executadas,
        "resposta_final": resposta,
    }
