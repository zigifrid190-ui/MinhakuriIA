import json
import httpx
import asyncio
from config import (
    GROK_API_KEY, GROK_MODEL, GROK_TEMPERATURE,
    GROK_MAX_TOKENS, GROK_URL, PROMPT_FILE, CONTEXT_WINDOW
)
from memory import (
    carregar_historico, adicionar_interacao, 
    carregar_perfil, carregar_ultimo_resumo,
    buscar_fatos_relevantes, salvar_resumo
)
from actions import TOOLS_SCHEMA, REGISTRY
from datetime import datetime

# Carrega o prompt de personalidade
try:
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        BASE_PROMPT = f.read()
except FileNotFoundError:
    print(f"[WARN] {PROMPT_FILE} nao encontrado. Usando prompt padrao.")
    BASE_PROMPT = "Você é a Kuri, uma assistente virtual brasileira sarcástica e carinhosa."

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

async def _gerar_resumo_background(historico: list):
    """Gera um resumo da conversa atual em segundo plano para não travar a resposta."""
    try:
        print("[BRAIN] Gerando resumo automático da sessão...")
        # Pega as últimas mensagens para o resumo
        mensagens_texto = "\n".join([f"{m['role']}: {m['content']}" for m in historico[-CONTEXT_WINDOW:]])
        
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
                    "messages": [{"role": "system", "content": "Você é um assistente de memória. Seja conciso."},
                                 {"role": "user", "content": prompt_resumo}],
                    "max_tokens": 150
                }
            )
            response.raise_for_status()
            resumo = response.json()["choices"][0]["message"]["content"].strip()
            salvar_resumo(resumo)
            print("[BRAIN] Resumo salvo com sucesso!")
    except Exception as e:
        print(f"[ERRO] Falha ao gerar resumo: {e}")

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

    return f"{BASE_PROMPT}\n\n{EMOTIONAL_CONTEXT}\n{SYSTEM_INSTRUCTIONS}\n{perfil_context}"


def _build_messages(texto: str, historico: list) -> list:
    messages = [{"role": "system", "content": _build_system_prompt(texto)}]

    for h in historico[-CONTEXT_WINDOW:]:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})

    messages.append({"role": "user", "content": texto})
    return messages

def _calcular_max_tokens(texto: str) -> int:
    # Ajusta o tamanho da resposta com base no tamanho do input
    # Evita que a Kuri dê respostas curtas demais para pedidos longos
    if texto.startswith("[SYSTEM_EVENT"):
        return 150 # Eventos proativos costumam ser curtos
    
    tamanho = len(texto)
    if tamanho < 30:
        return 150 # Comando curto
    elif tamanho < 100:
        return 250 # Pergunta normal
    else:
        return 450 # Texto longo (desabafo, explicação complexa)

async def pensar(texto: str) -> dict:
    """
    Processa a mensagem do usuário e retorna:
    {"resposta": str, "acao_executada": str | None}
    """
    historico = carregar_historico()
    
    # Verifica se deve gerar resumo (a cada CONTEXT_WINDOW mensagens)
    historico_len = len(historico)
    if historico_len > 0 and historico_len % CONTEXT_WINDOW == 0:
        asyncio.create_task(_gerar_resumo_background(historico))

    messages = _build_messages(texto, historico)

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                GROK_URL,
                headers={"Authorization": f"Bearer {GROK_API_KEY}"},
                json={
                    "model": GROK_MODEL,
                    "messages": messages,
                    "temperature": GROK_TEMPERATURE,
                    "max_tokens": _calcular_max_tokens(texto),
                    "tools": TOOLS_SCHEMA,
                    "tool_choice": "auto"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            choice = data["choices"][0]
            message = choice["message"]
            acao_executada = None

            # Verifica se a Kuri quer executar uma ferramenta
            if message.get("tool_calls"):
                tool_call = message["tool_calls"][0]
                func_name = tool_call["function"]["name"]
                func_args = json.loads(tool_call["function"]["arguments"])

                print(f"[TOOL] Kuri quer executar: {func_name}({func_args})")

                if func_name in REGISTRY:
                    acao_executada = REGISTRY[func_name](**func_args)
                    print(f"[OK] Resultado: {acao_executada}")

                    # Segunda chamada: Kuri comenta sobre a ação executada
                    messages.append(message)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": acao_executada
                    })

                    try:
                        follow_up = await client.post(
                            GROK_URL,
                            headers={"Authorization": f"Bearer {GROK_API_KEY}"},
                            json={
                                "model": GROK_MODEL,
                                "messages": messages,
                                "temperature": GROK_TEMPERATURE,
                                "max_tokens": 150 # Resposta de ação bem curta
                            }
                        )
                        follow_up.raise_for_status()
                        resposta = follow_up.json()["choices"][0]["message"]["content"]
                    except Exception:
                        resposta = acao_executada
                else:
                    resposta = f"Não sei executar a ação '{func_name}' ainda."
            else:
                resposta = message.get("content", "...")

        except httpx.HTTPStatusError as e:
            print(f"[ERRO] HTTP do Grok: {e.response.status_code} - {e.response.text[:200]}")
            return {"resposta": "Meu cérebro deu tela azul, velho. Tenta de novo.", "acao_executada": None}
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            print(f"[ERRO] Conexao com Grok: {e}")
            return {"resposta": "Sem internet, velho. Tô operando no modo offline.", "acao_executada": None}
        except Exception as e:
            print(f"[ERRO] Inesperado no brain: {e}")
            return {"resposta": "Deu ruim aqui. Erro genérico, manda de novo.", "acao_executada": None}

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

    return {"resposta": resposta, "acao_executada": acao_executada, "emocao": emocao}
