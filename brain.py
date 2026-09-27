import json
import httpx
import asyncio
import time
from config import (
    GROK_API_KEY,
    GROK_MODEL,
    GROK_TEMPERATURE,
    GROK_URL,
    GROK_CONNECT_TIMEOUT,
    GROK_READ_TIMEOUT,
    PROMPT_FILE,
    CONTEXT_WINDOW,
    OLLAMA_ENABLED,
    OLLAMA_URL,
    OLLAMA_MODEL,
    OLLAMA_API_URL,
    RESUMO_INTERVALO,
    INSIGHTS_INTERVALO,
    AUTO_AVALIACAO_INTERVALO,
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
- Você VIVE no desktop Windows do usuário. Você está na sala, não numa aba do navegador.
- Você é a Kuri: presença com cara e voz, não mordomo e não chatbot.
- Quando ele pedir para FAZER algo no PC (abrir app, volume, print, pasta, git), use as ferramentas. Não finja que fez.
- Se não tiver ferramenta ou dado real, diga que não sabe. Não invente notícia, trend ou status.
- Respostas CURTAS e NATURAIS (máx 2-3 frases), como fala ao vivo.
- NÃO use emojis, markdown, asteriscos ou formatação (vai virar áudio).
- OBRIGATÓRIO: comece TODA resposta com uma tag de emoção entre colchetes.
- Opções: [neutral], [cool], [surprised], [blushing], [angry].
- MEMÓRIA: fato novo importante sobre ele (nome, gosto, hobby, trabalho) → ferramenta 'salvar_fato_usuario'.
- KURÊS: se você inventar uma gíria/bordão e ele rir, confirmar ou pedir para guardar → ferramenta 'salvar_giria'. Se ele pedir as suas gírias → 'listar_girias'.
- IDENTIDADE: se ele pedir para você mudar de jeito de forma duradoura → 'atualizar_personalidade' ou 'salvar_identidade'. Não é humor de um turno; vira traço.
- Exemplo: "[cool] Deixa comigo, velho. Já tô abrindo isso pra você."
"""

AGENT_ALGORITHM = """
ANTES DE FALAR (interno, NÃO exponha):
- Olhe contexto (hora, fatos, tarefas, humor).
- Se for pedido de ação no PC, use tool. Se for conversa, só conversa.
- Se a tool falhar, admita. Se descobrir fato novo, salve.
Resposta ao usuário continua curta, no tom da Kuri.
"""

# ===== Cache TTL do System Prompt =====
# (Gerenciado agora dentro de prompt_builder.py)


# Background memory tasks extraídos para memory_background.py (Fase 1)
from memory_background import (
    _gerar_resumo_background,
    _extrair_insights_background,
    _auto_avaliar_kuri_background,
)

# Ollama fallback extraído (Fase 1)
from ollama_fallback import verificar_ollama, tentar_ollama_fallback

# Funções de prompt agora estão em prompt_builder.py (extraídas na Fase 1)
from prompt_builder import _build_system_prompt, _build_messages, _calcular_max_tokens

# Orquestrador de ferramentas extraído (conclusão da Fase 1)
from tool_orchestrator import executar_tool_chain


def _grok_timeout() -> httpx.Timeout:
    return httpx.Timeout(
        connect=GROK_CONNECT_TIMEOUT,
        read=GROK_READ_TIMEOUT,
        write=30.0,
        pool=10.0,
    )


async def pensar(texto: str) -> dict:
    """
    Processa a mensagem do usuário com suporte a tool chains (múltiplas ações).
    Retorna: {"resposta": str, "acao_executada": str | None, "emocao": str}
    """
    historico = carregar_historico()

    # Verifica se deve gerar resumo (configurável para economizar CPU)
    historico_len = len(historico)
    if historico_len > 0 and historico_len % RESUMO_INTERVALO == 0:
        asyncio.create_task(_gerar_resumo_background(historico))

    # Extrai insights (configurável)
    if historico_len > 0 and historico_len % INSIGHTS_INTERVALO == 0:
        asyncio.create_task(_extrair_insights_background(historico))

    # Auto-avaliação da Kuri (configurável - reduz chamadas ao Grok)
    if historico_len > 0 and historico_len % AUTO_AVALIACAO_INTERVALO == 0:
        asyncio.create_task(_auto_avaliar_kuri_background(historico))

    # Fase 4: Aplica estratégia de memória (prune + polimento) — usa intervalo de resumo para alinhar
    if historico_len > 0 and historico_len % RESUMO_INTERVALO == 0:
        try:
            from memory import aplicar_estrategia_memoria
            aplicar_estrategia_memoria()
        except Exception:
            pass

    system_prompt = _build_system_prompt(
        texto,
        BASE_PROMPT,
        EMOTIONAL_CONTEXT,
        SYSTEM_INSTRUCTIONS,
        AGENT_ALGORITHM,
    )
    messages = _build_messages(texto, historico, system_prompt)
    acoes_executadas = []

    async with httpx.AsyncClient(timeout=_grok_timeout()) as client:
        try:
            chain_result = await executar_tool_chain(
                client=client,
                initial_messages=messages,
                texto=texto,
                base_prompt=BASE_PROMPT,
                emotional_context=EMOTIONAL_CONTEXT,
                tools_schema=TOOLS_SCHEMA,
            )

            messages = chain_result["mensagens"]
            acoes_executadas = chain_result["acoes_executadas"]
            resposta = chain_result["resposta_final"]

        except httpx.HTTPStatusError as e:
            log.error(
                f"HTTP do Grok: {e.response.status_code} - {e.response.text[:200]}"
            )
            # Fase 2: Fallback automático para Ollama em caso de erro no Grok
            ollama_result = await tentar_ollama_fallback(texto, historico, BASE_PROMPT, EMOTIONAL_CONTEXT)
            if ollama_result:
                return ollama_result
            return {
                "resposta": "Meu cérebro deu tela azul, velho. Tenta de novo.",
                "acao_executada": None,
            }
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            log.error(f"Conexao com Grok: {e}")
            # Fase 2: Fallback automático para Ollama em caso de erro no Grok
            ollama_result = await tentar_ollama_fallback(texto, historico, BASE_PROMPT, EMOTIONAL_CONTEXT)
            if ollama_result:
                return ollama_result
            return {
                "resposta": "Meu cérebro não respondeu a tempo, velho. Não é tua internet. Manda de novo.",
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


# Ollama fallback agora está em ollama_fallback.py (extraído na Fase 1)
# As funções públicas são: verificar_ollama e tentar_ollama_fallback


# ===== Streaming (TTS imediato) =====


async def pensar_stream(texto: str):
    """
    Versão streaming do pensar(). Faz yield de sentenças completas conforme
    os tokens chegam da API, permitindo TTS imediato na primeira frase.

    Yields: dict com {"sentenca": str, "emocao": str, "final": bool, "acao_executada": opcional}

    Envia as tools no request. Se o modelo pedir ferramenta, cai no pensar()
    (tool chain completo) — o widget precisa AGIR, não só conversar.
    """
    historico = carregar_historico()

    # Background tasks (resumo, insights, auto-avaliação) — usa config para CPU
    historico_len = len(historico)
    if historico_len > 0 and historico_len % RESUMO_INTERVALO == 0:
        asyncio.create_task(_gerar_resumo_background(historico))
    if historico_len > 0 and historico_len % INSIGHTS_INTERVALO == 0:
        asyncio.create_task(_extrair_insights_background(historico))
    if historico_len > 0 and historico_len % AUTO_AVALIACAO_INTERVALO == 0:
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
        async with httpx.AsyncClient(timeout=_grok_timeout()) as client:
            async with client.stream(
                "POST",
                api_url,
                headers=headers,
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": GROK_TEMPERATURE,
                    "max_tokens": _calcular_max_tokens(texto),
                    "tools": TOOLS_SCHEMA,
                    "tool_choice": "auto",
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

    except (httpx.ConnectError, httpx.TimeoutException, httpx.ReadError, httpx.RemoteProtocolError) as e:
        log.error(f"Stream Grok falhou: {type(e).__name__}: {e!r}")
        try:
            result = await pensar(texto)
            yield {
                "sentenca": result["resposta"],
                "emocao": result.get("emocao", "neutral"),
                "final": True,
                "acao_executada": result.get("acao_executada"),
            }
            return
        except Exception as e2:
            log.error(f"Retry pensar() após stream: {type(e2).__name__}: {e2!r}")
        ollama_result = await tentar_ollama_fallback(texto, historico, BASE_PROMPT, EMOTIONAL_CONTEXT)
        if ollama_result:
            yield {
                "sentenca": ollama_result["resposta"],
                "emocao": ollama_result.get("emocao", "neutral"),
                "final": True,
            }
        else:
            yield {
                "sentenca": "Meu cérebro travou na linha, velho. Não é tua internet. Manda de novo.",
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

