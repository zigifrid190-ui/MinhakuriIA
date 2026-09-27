import functools
from typing import Callable, Any, Dict, List

class HookManager:
    def __init__(self):
        self.pre_hooks: List[Callable[[str, Dict[str, Any]], None]] = []
        self.post_hooks: List[Callable[[str, Dict[str, Any], Any], None]] = []

    def register_pre_hook(self, callback: Callable[[str, Dict[str, Any]], None]):
        self.pre_hooks.append(callback)

    def register_post_hook(self, callback: Callable[[str, Dict[str, Any], Any], None]):
        self.post_hooks.append(callback)

    def trigger_pre(self, name: str, args: Dict[str, Any]):
        for hook in self.pre_hooks:
            try:
                hook(name, args)
            except Exception as e:
                import logging
                logging.getLogger("kuri_skills").error(f"Erro no pre-hook da skill {name}: {e}")

    def trigger_post(self, name: str, args: Dict[str, Any], result: Any):
        for hook in self.post_hooks:
            try:
                hook(name, args, result)
            except Exception as e:
                import logging
                logging.getLogger("kuri_skills").error(f"Erro no post-hook da skill {name}: {e}")

hook_manager = HookManager()

class SkillRegistry:
    def __init__(self):
        self.registry: Dict[str, Callable] = {}
        self.schemas: List[Dict[str, Any]] = []

    def register(self, name: str, description: str, schema: Dict[str, Any] = None, dependencies: List[str] = None):
        def decorator(func: Callable):
            actual_schema = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": schema or {"type": "object", "properties": {}}
                }
            }
            
            # Armazena metadados de dependências para evolução da arquitetura (Fase 3)
            func._skill_dependencies = dependencies or []
            
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Executa pre-hooks
                hook_manager.trigger_pre(name, kwargs)
                try:
                    result = func(*args, **kwargs)
                    # Executa post-hooks com o sucesso
                    hook_manager.trigger_post(name, kwargs, result)
                    return result
                except Exception as e:
                    # Executa post-hooks com o erro
                    hook_manager.trigger_post(name, kwargs, f"Erro: {e}")
                    raise e

            self.registry[name] = wrapper
            self.schemas.append(actual_schema)
            return wrapper
        return decorator

    def clear(self):
        """Limpa o registro de skills para recarregamento dinâmico sem duplicatas."""
        self.registry.clear()
        self.schemas.clear()

    def get_dependencies(self, name: str) -> List[str]:
        """Retorna dependências declaradas de uma skill (Fase 3)."""
        func = self.registry.get(name)
        return getattr(func, "_skill_dependencies", []) if func else []

    def get_all_skills_with_meta(self) -> List[Dict[str, Any]]:
        """Retorna lista de skills com metadados para diagnóstico."""
        result = []
        for schema in self.schemas:
            name = schema["function"]["name"]
            deps = self.get_dependencies(name)
            result.append({
                "name": name,
                "description": schema["function"]["description"],
                "dependencies": deps,
                "schema": schema
            })
        return result

skill_registry = SkillRegistry()
skill = skill_registry.register
