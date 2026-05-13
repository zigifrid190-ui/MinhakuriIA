import json
import httpx
from config import (
    GROK_API_KEY, GROK_MODEL, GROK_TEMPERATURE,
    GROK_MAX_TOKENS, GROK_URL, PROMPT_FILE, CONTEXT_WINDOW
)
from memory import carregar_historico, adicionar_interacao, carregar_perfil
from actions import TOOLS_SCHEMA, REGISTRY

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
- Exemplo de resposta: "[cool] Deixa comigo, velho. Já tô abrindo isso pra você."
"""


def _build_system_prompt() -> str:
    perfil = carregar_perfil()
    perfil_context = ""
    if perfil.get("nome_usuario"):
        perfil_context += f"\nO nome do usuário é: {perfil['nome_usuario']}"
    if perfil.get("fatos_aprendidos"):
        fatos = "; ".join(perfil["fatos_aprendidos"][-10:])
        perfil_context += f"\nFatos sobre o usuário: {fatos}"

    return f"{BASE_PROMPT}\n\n{EMOTIONAL_CONTEXT}\n{SYSTEM_INSTRUCTIONS}\n{perfil_context}"


def _build_messages(texto: str, historico: list) -> list:
    messages = [{"role": "system", "content": _build_system_prompt()}]

    for h in historico[-CONTEXT_WINDOW:]:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})

    messages.append({"role": "user", "content": texto})
    return messages


async def pensar(texto: str) -> dict:
    """
    Processa a mensagem do usuário e retorna:
    {"resposta": str, "acao_executada": str | None}
    """
    historico = carregar_historico()
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
                    "max_tokens": GROK_MAX_TOKENS,
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
