import webbrowser
from kuri_skills.base import skill

@skill(
    name="pesquisar_web",
    description="Faz uma pesquisa no Google e abre no navegador.",
    schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "O que pesquisar"}
        },
        "required": ["query"],
    }
)
def pesquisar_web(query: str) -> str:
    url = f"https://www.google.com/search?q={query}"
    webbrowser.open(url)
    return f"Pesquisando '{query}' no Google pra você..."
