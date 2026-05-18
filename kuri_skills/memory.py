from kuri_skills.base import skill

@skill(
    name="salvar_fato_usuario",
    description="Salva um fato importante sobre o usuário (ex: 'ele gosta de café amargo', 'ele é programador').",
    schema={
        "type": "object",
        "properties": {
            "fato": {"type": "string", "description": "O fato a ser lembrado"}
        },
        "required": ["fato"],
    }
)
def salvar_fato_usuario(fato: str) -> str:
    """Salva uma informação importante sobre o usuário na memória de longo prazo."""
    from memory import adicionar_fato

    adicionar_fato(fato)
    return f"Fato memorizado: {fato}"


@skill(
    name="atualizar_perfil_usuario",
    description="Atualiza campos do perfil do usuário (nome_usuario, apelidos, humor_atual).",
    schema={
        "type": "object",
        "properties": {
            "campo": {
                "type": "string",
                "description": "Campo a atualizar",
                "enum": ["nome_usuario", "apelidos", "humor_atual"],
            },
            "valor": {"type": "string", "description": "Novo valor"},
        },
        "required": ["campo", "valor"],
    }
)
def atualizar_perfil_usuario(campo: str, valor: str) -> str:
    """Atualiza informações básicas do perfil (nome_usuario, humor_atual, etc)."""
    from memory import atualizar_perfil

    # Converte strings de lista para lista real se necessário
    if campo == "apelidos" and "," in valor:
        valor = [v.strip() for v in valor.split(",")]
    atualizar_perfil(campo, valor)
    return f"Perfil atualizado: {campo} = {valor}"
