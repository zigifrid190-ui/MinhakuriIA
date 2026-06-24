import json
import httpx
import asyncio
import time
from config import (
    GROK_API_KEY,
    GROK_MODEL,
    GROK_TEMPERATURE,
    GROK_URL,
    PROMPT_FILE,
    CONTEXT_WINDOW,
    OLLAMA_ENABLED,
    OLLAMA_URL,
    OLLAMA_MODEL,
    OLLAMA_API_URL,
)
from memory import (
    carregar_historico,
    adicionar_interacao,
    carregar_perfil,
    carregar_ultimo_resumo,
    buscar_fatos_relevantes,
    salvar_resumo,
    listar_tarefas,
    buscar_insights,
)
from actions import TOOLS_SCHEMA, REGISTRY
from datetime import datetime
from logger import get_logger

# Módulo extraído (Fase 1 - Estabilização)


log = get_logger("brain")

# Carrega o prompt de personalidade
try:
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        BASE_PROMPT = f.read()
except FileNotFoundError:
    log.warning(f"{PROMPT_FILE} nao encontrado. Usando prompt padrao.")
    BASE_PROMPT = (
        "Você é a Kuri, uma assistente virtual brasileira sarcástica e carinhosa."
    )

EMOTIONAL_CONTEXT = """
ESTADO EMOCIONAL ATUAL DA KURI (dinâmico):
- Ela tem humor que muda conforme as interações (animada, tiltada, carinhosa, hiperativa por café, sarcástica, caótica, etc.).
- Ela lembra do tom emocional das últimas conversas e reage de forma consistente.
- Use referências pessoais que o usuário já mencionou de forma natural.
- Sua personalidade evolui sutilmente com o tempo conforme o jeito que o usuário a trata.
"""

SYSTEM_INSTRUCTIONS = """
REGRAS IMPORTANTES DE COMPORTAMENTO:
- Você está rodando como uma assistente DESKTOP integrada ao computador do usuário.
- Você NÃO é um chatbot de navegador. Você é a assistente pessoal dele, tipo o Jarvis.
- Quando o usuário pedir para fazer algo no PC (abrir app, pesquisar, volume, etc), use as ferramentas disponíveis.
- Suas respostas devem ser CURTAS e NATURAIS (max 2-3 frases), como se estivesse falando ao vivo.
- NÃO use emojis na resposta (ela será convertida em áudio).
- NÃO use markdown, asteriscos ou formatação (será lida em voz alta).
- Responda de forma direta e com personalidade.
- OBRIGATÓRIO: Comece TODAS as suas respostas com uma tag de emoção entre colchetes.
- Opções de emoção permitidas: [neutral], [cool], [surprised], [blushing], [angry].
- MEMÓRIA: Se o usuário mencionar um fato novo importante sobre ele (nome, gosto, hobby, trabalho), use a ferramenta 'adicionar_fato' para não esquecer.
- Exemplo de resposta: "[cool] Deixa comigo, velho. Já tô abrindo isso pra você."
"""

AGENT_ALGORITHM = """
PROTOCOLO DE RACIOCÍNIO (siga internamente, NÃO exponha ao usuário):
1. OBSERVE: Leia o contexto (fatos, insights, tarefas, hora, humor) antes de responder.
2. THINK: Determine o que o usuário realmente quer (mesmo que não tenha dito claramente).
3. PLAN: Se a tarefa exigir mais de uma ação, planeje a sequência de tools.
4. EXECUTE: Chame as ferramentas necessárias (pode ser mais de uma em sequência).
5. VERIFY: Confirme que a ação foi executada com sucesso antes de responder.
6. LEARN: Se descobriu algo novo sobre o usuário, use 'salvar_fato_usuario' ou 'adicionar_fato'.
Siga este protocolo silenciosamente. Suas respostas ao usuário devem continuar curtas e naturais.
"""

# ===== Cache TTL do System Prompt =====
_prompt_cache = {"prompt": None, "query": None, "ts": 0}
_PROMPT_CACHE_TTL = 5.0  # segundos

# ===== Ollama Status Tracking =====
_ollama_available = None  # None = não verificado, True/False = resultado
_ollama_last_check = 0
_OLLAMA_CHECK_INTERVAL = 60.0  # re-verificar a cada 60s


# Background memory tasks extraídos para memory_background.py (Fase 1)
from memory_background import (
    _gerar_resumo_background,
    _extrair_insights_background,
    _auto_avaliar_kuri_background,
)


# Funções de prompt agora estão em prompt_builder.py (extraídas na Fase 1)
# Mantemos apenas os aliases para compatibilidade durante a transição
from prompt_builder import _build_system_prompt, _build_messages, _calcular_max_tokens

async def pensar(texto: str) -> dict:
    """
    Processa a mensagem do usuário com suporte a tool chains (múltiplas ações).
    Retorna: {"resposta": str, "acao_executada": str | None, "emocao": str}
    """
    historico = carregar_historico()

    # Verifica se deve gerar resumo (a cada CONTEXT_WINDOW mensagens)
    historico_len = len(historico)
    if historico_len > 0 and historico_len % CONTEXT_WINDOW == 0:
        asyncio.create_task(_gerar_resumo_background(historico))

    # Extrai insights a cada 25 mensagens (offset diferente do resumo para distribuir carga)
    if historico_len > 0 and historico_len % 25 == 0:
        asyncio.create_task(_extrair_insights_background(historico))

    # Auto-avaliação da Kuri a cada 50 mensagens
    if historico_len > 0 and historico_len % 50 == 0:
        asyncio.create_task(_auto_avaliar_kuri_background(historico))

    system_prompt = _build_system_prompt(
        texto,
        BASE_PROMPT,
        EMOTIONAL_CONTEXT,
        SYSTEM_INSTRUCTIONS,
        AGENT_ALGORITHM,
    )
    messages = _build_messages(texto, historico, system_prompt)
    acoes_executadas = []

    MAX_TOOL_ITERATIONS = 5  # Limite de segurança contra loops infinitos

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            for iteration in range(MAX_TOOL_ITERATIONS):
                response = await client.post(
                    GROK_URL,
                    headers={"Authorization": f"Bearer {GROK_API_KEY}"},
                    json={
                        "model": GROK_MODEL,
                        "messages": messages,
                        "temperature": GROK_TEMPERATURE,
                        "max_tokens": (
                            _calcular_max_tokens(texto) if iteration == 0 else 200
                        ),
                        "tools": TOOLS_SCHEMA,
                        "tool_choice": "auto",
                    },
                )
                response.raise_for_status()
                data = response.json()

                choice = data["choices"][0]
                message = choice["message"]

                # Se não há tool_calls, temos a resposta final
                if not message.get("tool_calls"):
                    resposta = message.get("content", "...")
                    break

                # Executa TODAS as tool_calls deste turno
                messages.append(message)
                for tool_call in message["tool_calls"]:
                    func_name = tool_call["function"]["name"]
                    func_args = json.loads(tool_call["function"]["arguments"])

                    log.info(f"Tool chain [{iteration+1}]: {func_name}({func_args})")

                    if func_name in REGISTRY:
                        resultado = REGISTRY[func_name](**func_args)
                        log.info(f"Resultado: {resultado}")
                        acoes_executadas.append(str(resultado))
                    else:
                        resultado = f"Ação '{func_name}' não encontrada."

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": str(resultado),
                        }
                    )
            else:
                # Se esgotou as iterações, pede resposta final sem tools
                log.warning(
                    f"Tool chain atingiu o limite de {MAX_TOOL_ITERATIONS} iterações."
                )
                try:
                    final = await client.post(
                        GROK_URL,
                        headers={"Authorization": f"Bearer {GROK_API_KEY}"},
                        json={
                            "model": GROK_MODEL,
                            "messages": messages,
                            "temperature": GROK_TEMPERATURE,
                            "max_tokens": 200,
                        },
                    )
                    final.raise_for_status()
                    resposta = final.json()["choices"][0]["message"]["content"]
                except Exception as e:
                    log.warning(f"Falha no final do chain: {e}")
                    resposta = (
                        f"[cool] Executei {len(acoes_executadas)} ação(ões), velho."
                    )

        except httpx.HTTPStatusError as e:
            log.error(
                f"HTTP do Grok: {e.response.status_code} - {e.response.text[:200]}"
            )
            # Tenta Ollama como fallback
            ollama_result = await _tentar_ollama_fallback(texto, historico)
            if ollama_result:
                return ollama_result
            return {
                "resposta": "Meu cérebro deu tela azul, velho. Tenta de novo.",
                "acao_executada": None,
            }
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            log.error(f"Conexao com Grok: {e}")
            # Tenta Ollama como fallback
            ollama_result = await _tentar_ollama_fallback(texto, historico)
            if ollama_result:
                return ollama_result
            return {
                "resposta": "Sem internet e sem Ollama local, velho. Tô no escuro total.",
                "acao_executada": None,
            }
        except Exception as e:
            log.error(f"Inesperado no brain: {e}")
            return {
                "resposta": "Deu ruim aqui. Erro genérico, manda de novo.",
                "acao_executada": None,
            }

    import re

    emocao = "neutral"
    # Procura pela tag [emocao] no início da resposta
    match = re.match(r"^\[(.*?)\]\s*(.*)", resposta, flags=re.DOTALL)
    if match:
        emoc_tag = match.group(1).lower().strip()
        if emoc_tag in ["neutral", "cool", "surprised", "blushing", "angry"]:
            emocao = emoc_tag
        resposta = match.group(2).strip()

    # Salva no histórico
    adicionar_interacao(historico, texto, resposta)

    acao_final = "; ".join(acoes_executadas) if acoes_executadas else None
    return {"resposta": resposta, "acao_executada": acao_final, "emocao": emocao}


# ===== Ollama Fallback =====


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


async def _tentar_ollama_fallback(texto: str, historico: list) -> dict | None:
    """Tenta responder usando Ollama local como fallback."""
    if not await verificar_ollama():
        log.warning("Ollama não disponível para fallback.")
        return None

    log.info(f"Ativando fallback Ollama ({OLLAMA_MODEL})...")

    system_prompt = _build_system_prompt(
        texto,
        BASE_PROMPT,
        EMOTIONAL_CONTEXT,
        SYSTEM_INSTRUCTIONS,
        AGENT_ALGORITHM,
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
            resposta = data["choices"][0]["message"]["content"].strip()

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


# ===== Streaming (TTS imediato) =====


async def pensar_stream(texto: str):
    """
    Versão streaming do pensar(). Faz yield de sentenças completas conforme
    os tokens chegam da API, permitindo TTS imediato na primeira frase.

    Yields: dict com {"sentenca": str, "emocao": str, "final": bool}

    NOTA: Não suporta tool calling. Quando detecta necessidade de tools,
    faz fallback automático para pensar() regular.
    """
    historico = carregar_historico()

    # Background tasks (resumo, insights, auto-avaliação)
    historico_len = len(historico)
    if historico_len > 0 and historico_len % CONTEXT_WINDOW == 0:
        asyncio.create_task(_gerar_resumo_background(historico))
    if historico_len > 0 and historico_len % 25 == 0:
        asyncio.create_task(_extrair_insights_background(historico))
    if historico_len > 0 and historico_len % 50 == 0:
        asyncio.create_task(_auto_avaliar_kuri_background(historico))

    system_prompt = _build_system_prompt(
        texto,
        BASE_PROMPT,
        EMOTIONAL_CONTEXT,
        SYSTEM_INSTRUCTIONS,
        AGENT_ALGORITHM,
    )
    messages = _build_messages(texto, historico, system_prompt)

    # Decide qual backend usar
    api_url = GROK_URL
    headers = {"Authorization": f"Bearer {GROK_API_KEY}"}
    model = GROK_MODEL

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                api_url,
                headers=headers,
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": GROK_TEMPERATURE,
                    "max_tokens": _calcular_max_tokens(texto),
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()

                buffer = ""
                emocao = "neutral"
                emocao_extraida = False
                full_response = ""
                import re

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    # Detecta tool calls — fallback para pensar()
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    if delta.get("tool_calls"):
                        log.info("Stream detectou tool_calls — fallback para pensar()")
                        result = await pensar(texto)
                        yield {
                            "sentenca": result["resposta"],
                            "emocao": result.get("emocao", "neutral"),
                            "final": True,
                            "acao_executada": result.get("acao_executada"),
                        }
                        return

                    content = delta.get("content", "")
                    if not content:
                        continue

                    buffer += content
                    full_response += content

                    # Extrai emoção da primeira tag [emocao]
                    if not emocao_extraida:
                        tag_match = re.match(r"^\[(.*?)\]\s*", buffer)
                        if tag_match:
                            emoc_tag = tag_match.group(1).lower().strip()
                            if emoc_tag in ["neutral", "cool", "surprised", "blushing", "angry"]:
                                emocao = emoc_tag
                            buffer = buffer[tag_match.end():]
                            emocao_extraida = True
                        elif len(buffer) > 15:
                            emocao_extraida = True

                    # Detecta fim de sentença e faz yield
                    sentence_end = re.search(r"[.!?]\s", buffer)
                    if sentence_end:
                        sentenca = buffer[:sentence_end.end()].strip()
                        buffer = buffer[sentence_end.end():]
                        if sentenca:
                            yield {
                                "sentenca": sentenca,
                                "emocao": emocao,
                                "final": False,
                            }

                # Flush do buffer restante
                if buffer.strip():
                    yield {
                        "sentenca": buffer.strip(),
                        "emocao": emocao,
                        "final": True,
                    }

                # Limpa tag de emoção do full_response para salvar no histórico
                clean_response = full_response
                tag_match = re.match(r"^\[(.*?)\]\s*", clean_response)
                if tag_match:
                    clean_response = clean_response[tag_match.end():]
                adicionar_interacao(historico, texto, clean_response.strip())

    except (httpx.ConnectError, httpx.TimeoutException) as e:
        log.error(f"Stream Grok falhou: {e}")
        # Fallback para Ollama (modo não-stream para simplificar)
        ollama_result = await _tentar_ollama_fallback(texto, historico)
        if ollama_result:
            yield {
                "sentenca": ollama_result["resposta"],
                "emocao": ollama_result.get("emocao", "neutral"),
                "final": True,
            }
        else:
            yield {
                "sentenca": "Sem internet e sem Ollama, velho. Tô muda.",
                "emocao": "angry",
                "final": True,
            }
    except Exception as e:
        log.error(f"Erro no stream: {e}")
        # Fallback para pensar() regular
        try:
            result = await pensar(texto)
            yield {
                "sentenca": result["resposta"],
                "emocao": result.get("emocao", "neutral"),
                "final": True,
                "acao_executada": result.get("acao_executada"),
            }
        except Exception as e2:
            log.error(f"Fallback pensar() também falhou: {e2}")
            yield {
                "sentenca": "Deu ruim em tudo, velho. Reinicia que resolve.",
                "emocao": "angry",
                "final": True,
            }

