from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
import base64
import json
from dotenv import load_dotenv
from typing import List, Dict, Any

load_dotenv()

app = FastAPI(title="Kuri IA - Emoções + Avatar 3D")

GROK_API = os.getenv("GROK_API_KEY")
ELEVEN_API = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
HEYGEN_API = os.getenv("HEYGEN_API_KEY")
AVATAR_ID = os.getenv("HEYGEN_AVATAR_ID")

# Caminho do arquivo de memória persistente
MEMORY_FILE = "kuri_memoria.json"

try:
    with open("prompt_kuri.txt", "r", encoding="utf-8") as f:
        BASE_PROMPT = f.read()
except FileNotFoundError:
    print("❌ Erro: Arquivo prompt_kuri.txt não encontrado.")
    BASE_PROMPT = "Você é a Kuri."


class Mensagem(BaseModel):
    texto: str
    history: List[Dict[str, Any]] = []


def carregar_memoria() -> List[Dict[str, Any]]:
    """Carrega o histórico de conversas do disco."""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Erro ao carregar memória: {e}")
    return []


def salvar_memoria(memoria: List[Dict[str, Any]]):
    """Salva o histórico de conversas no disco."""
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memoria, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erro ao salvar memória: {e}")


@app.post("/conversar")
async def conversar(msg: Mensagem):
    try:
        memoria_longa = carregar_memoria()

        # ==================== SISTEMA EMOCIONAL ====================
        emotional_context = """
        ESTADO EMOCIONAL ATUAL DA KURI (dinâmico):
        - Ela tem humor que muda conforme as interações (animada, tiltada, carinhosa, hiperativa por café, sarcástica, caótica, etc.).
        - Ela lembra do tom emocional das últimas conversas e reage de forma consistente.
        - Use referências pessoais que o usuário já mencionou de forma natural.
        - Sua personalidade evolui sutilmente com o tempo conforme o jeito que o usuário a trata.
        """

        system_prompt = f"{BASE_PROMPT}\n\n{emotional_context}\n\nLembre-se: Você é Kuri. Responda sempre considerando seu estado emocional atual, as interações anteriores e o tom do usuário.\nSeja dinâmica, reaja emocionalmente e evolua naturalmente."

        messages = [{"role": "system", "content": system_prompt}]

        # Mesclar histórico enviado pelo client + histórico longo salvo localmente
        todo_historico = memoria_longa + msg.history

        # Injetar apenas as últimas 20 mensagens no contexto para não gastar muitos tokens
        for h in todo_historico[-20:]:
            messages.append(
                {"role": h.get("role", "user"), "content": h.get("content", "")}
            )

        messages.append({"role": "user", "content": msg.texto})

        # Utilizando httpx para chamadas assíncronas (não bloqueia o servidor)
        async with httpx.AsyncClient(timeout=60.0) as client:

            # 1. Requisição Grok (LLM)
            try:
                grok_resp = await client.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROK_API}"},
                    json={
                        "model": "grok-4",
                        "messages": messages,
                        "temperature": 0.88,
                        "max_tokens": 450,
                    },
                )
                grok_resp.raise_for_status()  # Lança erro se status não for 2xx
                llm_response = grok_resp.json()["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"❌ Erro no Grok: {e}")
                return {
                    "resposta": "Foi mal velho, minha API de cérebro deu tela azul (erro no Grok).",
                    "audio_base64": None,
                    "video_url": None,
                }

            # Atualizar memória com a nova interação e salvar no disco
            memoria_longa.append({"role": "user", "content": msg.texto})
            memoria_longa.append({"role": "assistant", "content": llm_response})
            # Manter limite de 50 mensagens para o arquivo JSON não crescer infinitamente
            salvar_memoria(memoria_longa[-50:])

            # 2. Requisição ElevenLabs (Áudio)
            audio_base64 = None
            try:
                audio_resp = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
                    headers={"xi-api-key": ELEVEN_API},
                    json={
                        "text": llm_response,
                        "model_id": "eleven_turbo_v2_5",
                        "voice_settings": {
                            "stability": 0.65,
                            "similarity_boost": 0.85,
                            "style": 0.8,
                        },
                    },
                )
                audio_resp.raise_for_status()
                audio_base64 = base64.b64encode(audio_resp.content).decode("utf-8")
            except Exception as e:
                print(f"❌ Erro no ElevenLabs: {e}")

            # 3. Requisição HeyGen (Vídeo Avatar 3D)
            video_url = None
            if HEYGEN_API and AVATAR_ID:
                try:
                    print("🔄 Enviando requisição para HeyGen...")
                    heygen_resp = await client.post(
                        "https://api.heygen.com/v2/video/generate",
                        headers={
                            "X-Api-Key": HEYGEN_API,
                            "Content-Type": "application/json",
                        },
                        json={
                            "avatar_id": AVATAR_ID,
                            "script": {"type": "text", "input": llm_response},
                            "voice": {"type": "elevenlabs", "voice_id": VOICE_ID},
                            "background": "transparent",
                            "dimension": "720x1280",
                        },
                    )

                    if heygen_resp.status_code == 200:
                        video_data = heygen_resp.json()
                        video_url = video_data.get("data", {}).get("video_url")
                        print(f"✅ Vídeo gerado: {video_url}")
                    else:
                        print(f"❌ HeyGen falhou: {heygen_resp.text}")
                except Exception as e:
                    print(f"❌ Erro ao chamar HeyGen: {e}")

        return {
            "resposta": llm_response,
            "audio_base64": audio_base64,
            "video_url": video_url,
        }

    except Exception as e:
        print(f"Erro geral do endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


if __name__ == "__main__":
    import uvicorn

    print(
        "🚀 Kuri iniciada com sucesso: Memória Ativada, Chamadas Async (HTTPX), Tratamento de Erros."
    )
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
