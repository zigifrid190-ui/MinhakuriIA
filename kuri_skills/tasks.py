import os
from kuri_skills.base import skill

@skill(
    name="criar_pasta",
    description="Cria uma nova pasta na área de trabalho do usuário.",
    schema={
        "type": "object",
        "properties": {
            "nome": {
                "type": "string",
                "description": "Nome da pasta a ser criada",
            }
        },
        "required": ["nome"],
    }
)
def criar_pasta(nome: str) -> str:
    caminho = os.path.expanduser(f"~/Desktop/{nome}")
    try:
        os.makedirs(caminho, exist_ok=True)
        return f"Criei a pasta '{nome}' na sua área de trabalho!"
    except Exception as e:
        return f"Erro ao criar pasta: {e}"


@skill(
    name="abrir_pasta",
    description="Abre uma pasta do sistema (downloads, documentos, desktop, etc).",
    schema={
        "type": "object",
        "properties": {
            "caminho": {
                "type": "string",
                "description": "Nome da pasta (downloads, documentos, desktop, imagens, musicas, videos) ou caminho absoluto",
            }
        },
        "required": ["caminho"],
    }
)
def abrir_pasta(caminho: str) -> str:
    expanded = os.path.expanduser(caminho)
    pastas_conhecidas = {
        "downloads": os.path.expanduser("~/Downloads"),
        "documentos": os.path.expanduser("~/Documents"),
        "desktop": os.path.expanduser("~/Desktop"),
        "area de trabalho": os.path.expanduser("~/Desktop"),
        "imagens": os.path.expanduser("~/Pictures"),
        "musicas": os.path.expanduser("~/Music"),
        "videos": os.path.expanduser("~/Videos"),
    }

    alvo = pastas_conhecidas.get(caminho.lower().strip(), expanded)

    if os.path.isdir(alvo):
        os.startfile(alvo)
        return "Abrindo a pasta..."
    return f"Não encontrei a pasta '{caminho}'."


@skill(
    name="gerenciar_tarefa",
    description="Gerencia a lista de tarefas (To-Do) do usuário. Use para criar, concluir ou remover itens.",
    # dependencies=["outra_skill"],  # Exemplo Fase 3
    schema={
        "type": "object",
        "properties": {
            "acao": {
                "type": "string",
                "description": "Ação a realizar",
                "enum": ["criar", "concluir", "remover"],
            },
            "titulo": {
                "type": "string",
                "description": "Título da tarefa (apenas para 'criar')",
            },
            "task_id": {
                "type": "integer",
                "description": "ID da tarefa (para 'concluir' ou 'remover')",
            },
            "prioridade": {
                "type": "integer",
                "description": "Prioridade de 1 a 3 (3 é urgente)",
                "default": 1,
            },
        },
        "required": ["acao"],
    }
)
def gerenciar_tarefa(
    acao: str, titulo: str = None, task_id: int = None, prioridade: int = 1
) -> str:
    """Cria, conclui ou remove tarefas da lista do usuário."""
    from memory import adicionar_tarefa, concluir_tarefa, remover_tarefa

    if acao == "criar":
        if not titulo:
            return "Preciso de um título para criar a tarefa, velho."
        adicionar_tarefa(titulo, prioridade)
        return f"Beleza, anotei aqui: '{titulo}'."

    elif acao == "concluir":
        if task_id is None:
            return "Qual o ID da tarefa que tu terminou?"
        if concluir_tarefa(task_id):
            return f"Boa! Marquei a tarefa {task_id} como feita."
        return f"Não achei nenhuma tarefa com o ID {task_id}."

    elif acao == "remover":
        if task_id is None:
            return "Qual o ID da tarefa para deletar?"
        if remover_tarefa(task_id):
            return f"Tarefa {task_id} removida do seu histórico."
        return f"ID {task_id} não encontrado."

    return f"Ação de tarefa desconhecida: {acao}"


@skill(
    name="listar_minhas_tarefas",
    description="Retorna a lista de todas as tarefas pendentes do usuário.",
    schema={"type": "object", "properties": {}}
)
def listar_minhas_tarefas() -> str:
    """Retorna uma lista formatada das tarefas pendentes."""
    from memory import listar_tarefas

    tasks = listar_tarefas(apenas_pendentes=True)
    if not tasks:
        return "Tu tá livre, velho! Nenhuma tarefa pendente."

    output = "Aqui o que tu tem pra fazer:\n"
    for t in tasks:
        prio = "🔥" if t["prioridade"] >= 3 else "⚡" if t["prioridade"] == 2 else "📝"
        output += f"- [{t['id']}] {prio} {t['titulo']}\n"
    return output
