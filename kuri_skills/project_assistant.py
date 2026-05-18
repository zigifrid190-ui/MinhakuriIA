import subprocess
import os
from kuri_skills.base import skill

def _run_git_cmd(args: list, cwd: str = None) -> str:
    """Executa um comando Git com segurança e retorna a saída formatada."""
    try:
        # Garante que git esteja no path e roda o comando
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=cwd or os.getcwd(),
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return f"Erro Git (código {result.returncode}): {result.stderr.strip()}"
    except FileNotFoundError:
        return "Git não está instalado ou não foi encontrado no PATH do sistema, velho."
    except Exception as e:
        return f"Falha ao executar comando Git: {e}"

@skill(
    name="git_status",
    description="Retorna o status simplificado do repositório Git local (arquivos modificados, branch atual).",
    schema={
        "type": "object",
        "properties": {
            "repo_path": {
                "type": "string",
                "description": "Caminho absoluto do repositório Git (opcional, usa a raiz do projeto por padrão)"
            }
        }
    }
)
def git_status(repo_path: str = None) -> str:
    """Obtém informações rápidas sobre o estado do git no repositório."""
    cwd = repo_path or os.getcwd()
    
    # Verifica se é um repositório git
    if not os.path.exists(os.path.join(cwd, ".git")):
        return f"A pasta '{cwd}' não parece ser um repositório Git ativo, velho."

    branch = _run_git_cmd(["branch", "--show-current"], cwd=cwd)
    status_short = _run_git_cmd(["status", "-s"], cwd=cwd)
    
    if not status_short:
        return f"Branch: {branch}\n[Tudo limpo] Nenhuma alteração pendente de commit, velho!"
    
    return f"Branch atual: {branch}\nAlterações pendentes:\n{status_short}"

@skill(
    name="listar_projetos_desenvolvimento",
    description="Varre um diretório base buscando projetos de desenvolvimento que contenham repositórios Git.",
    schema={
        "type": "object",
        "properties": {
            "diretorio_base": {
                "type": "string",
                "description": "Caminho do diretório pai para buscar projetos (opcional, usa a pasta Documentos/Projetos por padrão)"
            }
        }
    }
)
def listar_projetos_desenvolvimento(diretorio_base: str = None) -> str:
    """Varre diretórios para localizar repositórios Git ativos do desenvolvedor."""
    # Caminho default elegante
    default_dir = os.path.expanduser(r"~\Documents\Projetos IA")
    if not os.path.exists(default_dir):
        default_dir = os.path.expanduser(r"~\Documents")
        
    base = diretorio_base or default_dir
    if not os.path.exists(base):
        return f"Diretório base de busca não encontrado: {base}"
        
    try:
        projetos = []
        for name in os.listdir(base):
            full_path = os.path.join(base, name)
            if os.path.isdir(full_path):
                if os.path.exists(os.path.join(full_path, ".git")):
                    projetos.append(name)
        
        if not projetos:
            return f"Não achei nenhum projeto Git na pasta '{base}', velho."
            
        lines = [f"- {p} (em {os.path.join(base, p)})" for p in projetos]
        return f"Projetos localizados em {base}:\n" + "\n".join(lines)
    except Exception as e:
        return f"Erro ao listar projetos de desenvolvimento: {e}"

@skill(
    name="resumo_projeto",
    description="Analisa o README.md ou ROADMAP.md de um projeto para dar contexto rápido sobre as metas do repositório.",
    schema={
        "type": "object",
        "properties": {
            "projeto_path": {
                "type": "string",
                "description": "Caminho absoluto da pasta do projeto"
            }
        },
        "required": ["projeto_path"]
    }
)
def resumo_projeto(projeto_path: str) -> str:
    """Lê e resume arquivos de contexto de projetos de código."""
    if not os.path.exists(projeto_path):
        return f"Caminho do projeto não encontrado: {projeto_path}"
        
    readme_files = ["README.md", "README.txt", "readme.md", "ROADMAP.md", "roadmap.md"]
    content_found = None
    file_used = None
    
    for filename in readme_files:
        path = os.path.join(projeto_path, filename)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content_found = f.read(1500)  # Limite seguro
                    file_used = filename
                    break
            except Exception:
                continue
                
    if not content_found:
        return f"Não achei README ou ROADMAP legível na pasta '{projeto_path}', velho."
        
    info = f"Conteúdo do {file_used} (Resumo inicial):\n---\n{content_found}\n---"
    if len(content_found) >= 1500:
        info += "\n(Conteúdo truncado para economia de contexto...)"
    return info

@skill(
    name="sugerir_proximos_passos",
    description="Analisa alterações Git e arquivos de roadmap para propor as próximas tarefas do desenvolvedor.",
    schema={
        "type": "object",
        "properties": {
            "projeto_path": {
                "type": "string",
                "description": "Caminho absoluto da pasta do projeto (opcional, usa a raiz do projeto padrão)"
            }
        }
    }
)
def sugerir_proximos_passos(projeto_path: str = None) -> str:
    """Combina status git e roadmap para propor ações de desenvolvimento proativas."""
    cwd = projeto_path or os.getcwd()
    
    status = git_status(repo_path=cwd)
    resumo = resumo_projeto(projeto_path=cwd)
    
    proposta = f"=== Status de Trabalho ===\n{status}\n\n=== Contexto do Projeto ===\n{resumo}\n"
    proposta += "\nBaseado nisso, proponha sugestões de desenvolvimento, refatoração ou correções apropriadas, velho."
    return proposta
