import json
import os
from typing import Any
from config import MEMORY_FILE, PROFILE_FILE, MAX_MEMORY_MESSAGES


def carregar_json(path: str) -> list | dict:
    if not os.path.exists(path):
        return [] if path == MEMORY_FILE else {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"[WARN] Erro ao carregar {path}: {e}")
        return [] if path == MEMORY_FILE else {}


def salvar_json(path: str, data: list | dict):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"[WARN] Erro ao salvar {path}: {e}")


def carregar_historico() -> list[dict[str, Any]]:
    return carregar_json(MEMORY_FILE)


def salvar_historico(historico: list[dict[str, Any]]):
    salvar_json(MEMORY_FILE, historico[-MAX_MEMORY_MESSAGES:])


def adicionar_interacao(historico: list, user_msg: str, assistant_msg: str) -> list:
    historico.append({"role": "user", "content": user_msg})
    historico.append({"role": "assistant", "content": assistant_msg})
    salvar_historico(historico)
    return historico


def carregar_perfil() -> dict:
    perfil = carregar_json(PROFILE_FILE)
    if not perfil:
        perfil = {
            "nome_usuario": "",
            "apelidos": [],
            "humor_atual": "neutra",
            "fatos_aprendidos": []
        }
        salvar_json(PROFILE_FILE, perfil)
    return perfil


def atualizar_perfil(campo: str, valor: Any):
    perfil = carregar_perfil()
    perfil[campo] = valor
    salvar_json(PROFILE_FILE, perfil)


def adicionar_fato(fato: str):
    perfil = carregar_perfil()
    if fato not in perfil.get("fatos_aprendidos", []):
        perfil.setdefault("fatos_aprendidos", []).append(fato)
        salvar_json(PROFILE_FILE, perfil)
