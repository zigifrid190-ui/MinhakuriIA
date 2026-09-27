import httpx
import os
from kuri_skills.base import skill
import logging

log = logging.getLogger("kuri_skills")

def _obter_reddit_hot(subreddit: str) -> str:
    """Busca posts populares de um subreddit usando a API JSON pública do Reddit."""
    try:
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=5"
        headers = {"User-Agent": "KuriDesktopAssistant/1.0.0"}
        
        response = httpx.get(url, headers=headers, timeout=10.0)
        if response.status_code == 200:
            data = response.json()
            posts = data.get("data", {}).get("children", [])
            if not posts:
                return f"Nenhum post encontrado em r/{subreddit}."
            
            lines = []
            for p in posts[:3]:
                post_data = p.get("data", {})
                title = post_data.get("title", "")
                score = post_data.get("score", 0)
                url_post = post_data.get("url", "")
                lines.append(f"- [{subreddit}] {title} (Likes: {score}) -> {url_post}")
            return "\n".join(lines)
        return f"Não consegui ler o Reddit r/{subreddit} (HTTP {response.status_code})."
    except Exception as e:
        return f"Erro ao acessar r/{subreddit}: {e}"

@skill(
    name="checar_redes_sociais",
    description="Consulta posts reais do Reddit. YouTube, Discord e Twitter só se houver dado de verdade — nunca inventa trend.",
    schema={
        "type": "object",
        "properties": {
            "plataforma": {
                "type": "string",
                "description": "A plataforma a monitorar: youtube, reddit, discord, twitter, todas",
                "enum": ["youtube", "reddit", "discord", "twitter", "todas"]
            }
        }
    }
)
def checar_redes_sociais(plataforma: str = "todas") -> str:
    """Verifica e reporta as últimas novidades nas redes sociais configuradas."""
    plat = plataforma.lower().strip()
    report = []
    
    # 1. REDDIT (Live - Puxando novidades de IA e Python!)
    if plat in ["reddit", "todas"]:
        report.append("=== Reddit AI & Python Trends ===")
        report.append(_obter_reddit_hot("LocalLlama"))
        report.append(_obter_reddit_hot("Python"))
        report.append("")
        
    # 2. YouTube / X / Discord — sem API ainda. Mentir quebra a personagem.
    if plat in ["youtube", "todas"]:
        report.append("=== YouTube ===")
        report.append("Ainda não tenho API do YouTube, velho. Não vou inventar vídeo.")
        report.append("")

    if plat in ["discord", "twitter", "todas"]:
        report.append("=== Discord / X ===")
        discord_webhook = os.getenv("DISCORD_MONITOR_WEBHOOK")
        if discord_webhook:
            report.append("- Discord: webhook configurado, mas eu ainda não leio o canal de verdade.")
        else:
            report.append("- Discord: sem webhook no .env.")
        report.append("- Twitter/X: sem API. Não tenho trend real pra te contar.")
        report.append("")
        
    final_report = "\n".join(report).strip()
    return final_report or "Nenhuma plataforma válida especificada, velho."
