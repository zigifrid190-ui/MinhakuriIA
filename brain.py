import json
import httpx
import asyncio
from config import (
    GROK_API_KEY,
    GROK_MODEL,
    GROK_TEMPERATURE,
    GROK_URL,
    PROMPT_FILE,
    CONTEXT_WINDOW,
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


async def _gerar_resumo_background(historico: list):
    """Gera um resumo da conversa atual em segundo plano para não travar a resposta."""
    try:
        log.info("Gerando resumo automático da sessão...")
        # Pega as últimas mensagens para o resumo
        mensagens_texto = "\n".join(
            [f"{m['role']}: {m['content']}" for m in historico[-CONTEXT_WINDOW:]]
        )

        prompt_resumo = (
            "Resuma os pontos principais desta conversa entre a Kuri (IA) e o Usuário em 3 tópicos curtos e diretos. "
            "Foque em fatos aprendidos, decisões tomadas ou o clima da conversa.\n\n"
            f"Conversa:\n{mensagens_texto}"
        )

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                GROK_URL,
                headers={"Authorization": f"Bearer {GROK_API_KEY}"},
                json={
                    "model": GROK_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Você é um assistente de memória. Seja conciso.",
                        },
                        {"role": "user", "content": prompt_resumo},
                    ],
                    "max_tokens": 150,
                },
            )
            response.raise_for_status()
            resumo = response.json()["choices"][0]["message"]["content"].strip()
            salvar_resumo(resumo)
            log.info("Resumo salvo com sucesso!")
    except Exception as e:
        log.error(f"Falha ao gerar resumo: {e}")


async def _extrair_insights_background(historico: list):
    """Extrai insights comportamentais do usuário a partir do histórico recente."""
    try:
        log.info("Extraindo insights comportamentais...")
        mensagens_texto = "\n".join(
            [f"{m['role']}: {m['content']}" for m in historico[-CONTEXT_WINDOW:]]
        )

        prompt_insights = (
            "Analise esta conversa entre a Kuri (IA) e o Usuário. "
            "Extraia NO MÁXIMO 3 insights sobre o usuário. "
            "Cada insight deve ter o formato JSON:\n"
            '[{"tipo": "preferencia|habito|estilo|assunto", "conteudo": "descrição curta", "confianca": 0.5}]\n'
            "Retorne APENAS o JSON array, sem texto extra. Se não houver insights claros, retorne [].\n\n"
            f"Conversa:\n{mensagens_texto}"
        )

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                GROK_URL,
                headers={"Authorization": f"Bearer {GROK_API_KEY}"},
                json={
                    "model": GROK_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Você é um analisador de comportamento. Retorne apenas JSON.",
                        },
                        {"role": "user", "content": prompt_insights},
                    ],
                    "max_tokens": 200,
                },
            )
            response.raise_for_status()
            raw = response.json()["choices"][0]["message"]["content"].strip()

            # Parse seguro do JSON
            import re as _re

            match = _re.search(r"\[.*\]", raw, flags=_re.DOTALL)
            if match:
                from memory import adicionar_insight

                insights = json.loads(match.group())
                for ins in insights:
                    adicionar_insight(
                        tipo=ins.get("tipo", "assunto"),
                        conteudo=ins.get("conteudo", ""),
                        confianca=float(ins.get("confianca", 0.5)),
                    )
                log.info(f"{len(insights)} insight(s) extraído(s) e salvo(s).")
    except Exception as e:
        log.error(f"Falha ao extrair insights: {e}")


async def _auto_avaliar_kuri_background(historico: list):
    """Realiza uma auto-avaliação autônoma do desempenho e do tom da Kuri."""
    try:
        log.info("Iniciando auto-avaliação comportamental da Kuri...")
        mensagens_texto = "\n".join(
            [f"{m['role']}: {m['content']}" for m in historico[-50:]]
        )

        prompt_avaliacao = (
            "Analise as últimas 50 interações da Kuri (IA) com o Usuário para auto-avaliação.\n"
            "Avalie o nível de satisfação do usuário, a eficácia do tom adotado pela Kuri, "
            "e identifique se há áreas de contradição, inconsistências ou oportunidades de melhoria comportamental.\n"
            "Gere uma resposta em formato JSON rígido seguindo este schema:\n"
            "{\n"
            '  "satisfacao_usuario": "alta | media | baixa",\n'
            '  "perfil_psicologico_usuario": "análise curta dos traços psicológicos revelados nesta sessão",\n'
            '  "sugestao_ajuste_humor_kuri": "sugestão de humor predominante (ex: sarcástica, empática, séria, focada)",\n'
            '  "pontos_melhoria": ["ponto 1", "ponto 2"]\n'
            "}\n"
            "Retorne APENAS o objeto JSON. Não coloque markdown block como ```json ou qualquer texto extra.\n\n"
            f"Histórico das conversas:\n{mensagens_texto}"
        )

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                GROK_URL,
                headers={"Authorization": f"Bearer {GROK_API_KEY}"},
                json={
                    "model": GROK_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Você é um auditor de inteligência artificial focado em avaliar alinhamento e consistência comportamental.",
                        },
                        {"role": "user", "content": prompt_avaliacao},
                    ],
                    "max_tokens": 400,
                },
            )
            response.raise_for_status()
            raw = response.json()["choices"][0]["message"]["content"].strip()

            import re as _re
            match = _re.search(r"\{.*\}", raw, flags=_re.DOTALL)
            if match:
                from memory import atualizar_perfil
                avaliacao_json = match.group()
                atualizar_perfil("auto_avaliacao_recente", avaliacao_json)
                log.info("Auto-avaliação autônoma realizada e salva no perfil com sucesso.")
    except Exception as e:
        log.error(f"Falha ao realizar auto-avaliação comportamental: {e}")


def _get_temporal_context() -> str:
    now = datetime.now()
    hour = now.hour

    dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    weekday = dias_semana[now.weekday()]

    if hour < 6:
        return f"São {now.strftime('%H:%M')} de madrugada ({weekday}). O usuário tá acordado tarde. Comente isso de forma natural se couber."
    elif hour < 12:
        return f"São {now.strftime('%H:%M')} da manhã ({weekday}). Bom dia, energia matinal."
    elif hour < 18:
        return f"São {now.strftime('%H:%M')} da tarde ({weekday}). Modo produtivo."
    else:
        return f"São {now.strftime('%H:%M')} da noite ({weekday}). Modo relaxado ou ranked de noite."


def _build_system_prompt(query: str) -> str:
    perfil = carregar_perfil()
    perfil_context = ""

    # Contexto Temporal
    perfil_context += f"\nContexto Temporal Atual: {_get_temporal_context()}"

    # Contexto de Perfil e Memória
    if perfil.get("nome_usuario"):
        perfil_context += f"\nO nome do usuário é: {perfil['nome_usuario']}"

    humor = perfil.get("humor_atual", "neutra")
    perfil_context += f"\nSeu humor atual (mantenha a consistência): {humor}"

    fatos_relevantes = buscar_fatos_relevantes(query)
    if fatos_relevantes:
        fatos = "; ".join(fatos_relevantes)
        perfil_context += f"\nFatos memorizados RELEVANTES AGORA: {fatos}"

    # Contexto de Longo Prazo (Resumo anterior)
    ultimo_resumo = carregar_ultimo_resumo()
    if ultimo_resumo:
        perfil_context += f"\nContexto de conversas passadas: {ultimo_resumo}"

    # Contexto de Tarefas Pendentes
    tasks = listar_tarefas(apenas_pendentes=True)
    if tasks:
        task_list = "; ".join([f"[{t['id']}] {t['titulo']}" for t in tasks[:5]])
        perfil_context += f"\nTarefas Pendentes do Usuário: {task_list}"

    # Insights Comportamentais (Aprendizado Contínuo)
    insights = buscar_insights(limit=5)
    if insights:
        ins_text = "; ".join([f"[{i['tipo']}] {i['conteudo']}" for i in insights])
        perfil_context += (
            f"\nInsights sobre o usuário (use com naturalidade): {ins_text}"
        )

    # Auto-avaliação e Ajuste de Tom Emocional
    auto_eval = perfil.get("auto_avaliacao_recente")
    if auto_eval:
        try:
            eval_data = json.loads(auto_eval)
            sugestao = eval_data.get("sugestao_ajuste_humor_kuri")
            melhorias = ", ".join(eval_data.get("pontos_melhoria", []))
            if sugestao:
                perfil_context += f"\n[Auto-análise Comportamental]: A partir da sua última auto-avaliação, tente adotar um tom mais '{sugestao}' nas interações."
            if melhorias:
                perfil_context += f" Atente para estes pontos de melhoria: {melhorias}."
        except Exception:
            pass

    return f"{BASE_PROMPT}\n\n{EMOTIONAL_CONTEXT}\n{SYSTEM_INSTRUCTIONS}\n{AGENT_ALGORITHM}\n{perfil_context}"


def _build_messages(texto: str, historico: list) -> list:
    messages = [{"role": "system", "content": _build_system_prompt(texto)}]

    for h in historico[-CONTEXT_WINDOW:]:
        messages.append(
            {"role": h.get("role", "user"), "content": h.get("content", "")}
        )

    messages.append({"role": "user", "content": texto})
    return messages


def _calcular_max_tokens(texto: str) -> int:
    # Ajusta o tamanho da resposta com base no tamanho do input
    # Evita que a Kuri dê respostas curtas demais para pedidos longos
    if texto.startswith("[SYSTEM_EVENT"):
        return 150  # Eventos proativos costumam ser curtos

    tamanho = len(texto)
    if tamanho < 30:
        return 150  # Comando curto
    elif tamanho < 100:
        return 250  # Pergunta normal
    else:
        return 450  # Texto longo (desabafo, explicação complexa)


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

    messages = _build_messages(texto, historico)
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
            return {
                "resposta": "Meu cérebro deu tela azul, velho. Tenta de novo.",
                "acao_executada": None,
            }
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            log.error(f"Conexao com Grok: {e}")
            return {
                "resposta": "Sem internet, velho. Tô operando no modo offline.",
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
