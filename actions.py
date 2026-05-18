import os
import sys
import importlib
import subprocess  # noqa: F401
import webbrowser  # noqa: F401
from datetime import datetime  # noqa: F401
from logger import get_logger
from kuri_skills.base import skill_registry, hook_manager
import memory

log = get_logger("actions")

# Diretorio absoluto de skills
SKILLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kuri_skills")

# Inicializamos o dicionário e a lista que serão exportados para o brain.py
REGISTRY = {}
TOOLS_SCHEMA = []

def load_dynamic_skills():
    """Carrega dinamicamente todos os módulos de skill e atualiza o registro público."""
    global REGISTRY, TOOLS_SCHEMA

    log.info("Iniciando carregamento dinâmico de skills...")

    # Limpa as funções antigas do globals() para evitar vazamentos de ferramentas excluídas
    for old_name in list(REGISTRY.keys()):
        if old_name in globals():
            del globals()[old_name]

    # Limpa o registro central do base.py
    skill_registry.clear()

    # Garante que a pasta pai de kuri_skills está no path do Python
    parent_dir = os.path.dirname(SKILLS_DIR)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    # Varre a pasta kuri_skills
    if not os.path.exists(SKILLS_DIR):
        log.error(f"Diretório de skills não encontrado: {SKILLS_DIR}")
        return

    for filename in os.listdir(SKILLS_DIR):
        if filename.endswith(".py") and not filename.startswith("_") and filename != "base.py":
            module_name = f"kuri_skills.{filename[:-3]}"
            try:
                if module_name in sys.modules:
                    # Recarrega o módulo se ele já tiver sido importado anteriormente
                    importlib.reload(sys.modules[module_name])
                    log.info(f"Skill recarregada: {module_name}")
                else:
                    importlib.import_module(module_name)
                    log.info(f"Skill importada: {module_name}")
            except Exception as e:
                log.error(f"Erro ao carregar módulo de skill '{module_name}': {e}")

    # Atualiza as referências locais com os dados do registro central
    REGISTRY.clear()
    REGISTRY.update(skill_registry.registry)
    
    TOOLS_SCHEMA.clear()
    TOOLS_SCHEMA.extend(skill_registry.schemas)

    # Exporta dinamicamente as funções registradas para o escopo global deste módulo
    # Isso preserva 100% da compatibilidade com 'from actions import abrir_aplicativo' etc.
    for name, func in REGISTRY.items():
        globals()[name] = func

    log.info(f"Carregamento concluído! {len(REGISTRY)} skills prontas para uso.")

# ===== Definição de Hooks Padrão =====

def _log_pre_hook(name: str, args: dict):
    log.info(f"[HOOK PRE] Chamando ferramenta '{name}' com argumentos: {args}")

def _log_post_hook(name: str, args: dict, result: any):
    log.info(f"[HOOK POST] Ferramenta '{name}' finalizada. Resultado: {result}")
    
    # Salva no banco de dados SQLite para fins de auditoria e aprendizado contínuo (Padrão PAI)
    try:
        memory.adicionar_historico_acao(nome_acao=name, argumentos=args, resultado=result)
    except Exception as e:
        log.error(f"Falha ao salvar histórico de ação via hook no SQLite: {e}")

# Registra os hooks centrais
hook_manager.register_pre_hook(_log_pre_hook)
hook_manager.register_post_hook(_log_post_hook)

# Executa o carregamento inicial ao importar o módulo
load_dynamic_skills()
