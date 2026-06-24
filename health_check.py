"""
health_check.py
Adicionado durante Fase 1 de Estabilização.

Verifica se o ambiente está saudável antes de iniciar a Kuri.
"""
import os
import sys
from logger import get_logger

log = get_logger("health")

def check_environment() -> dict:
    """Retorna status de saúde do sistema."""
    status = {
        "python_version": sys.version.split()[0],
        "has_grok_key": bool(os.getenv("GROK_API_KEY")),
        "has_elevenlabs_key": bool(os.getenv("ELEVENLABS_API_KEY")),
        "ok": True,
        "warnings": [],
    }

    if not status["has_grok_key"]:
        status["warnings"].append("GROK_API_KEY não configurada")
        status["ok"] = False

    # Verifica se pastas importantes existem
    for folder in ["kuri_skills", "gui", "models"]:
        if not os.path.isdir(folder):
            status["warnings"].append(f"Pasta '{folder}' não encontrada")
            status["ok"] = False

    if status["warnings"]:
        log.warning("Health check warnings: %s", status["warnings"])
    else:
        log.info("Health check: Ambiente OK")

    return status


if __name__ == "__main__":
    print(check_environment())