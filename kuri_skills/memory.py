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


@skill(
    name="salvar_giria",
    description="Guarda uma gíria ou bordão da Kuri (Kurês). Use quando ela inventar uma expressão e o usuário rir, confirmar ou pedir para salvar.",
    schema={
        "type": "object",
        "properties": {
            "giria": {"type": "string", "description": "A expressão em si (ex: 'café na veia nuclear')"},
            "sentido": {"type": "string", "description": "O que significa, em uma frase curta"},
        },
        "required": ["giria"],
    },
)
def salvar_giria(giria: str, sentido: str = "") -> str:
    from memory import adicionar_giria

    ok = adicionar_giria(giria, sentido or "", origem="kuri")
    if not ok:
        return "Não rolou salvar essa gíria, velho."
    if sentido:
        return f"Anotei no Kurês: '{giria}' — {sentido}"
    return f"Anotei no Kurês: '{giria}'"


@skill(
    name="listar_girias",
    description="Lista as gírias ativas do Kurês, a língua da Kuri.",
    schema={"type": "object", "properties": {}},
)
def listar_girias_skill() -> str:
    from memory import listar_girias

    itens = listar_girias(apenas_ativas=True, limit=20)
    if not itens:
        return "Ainda não tenho Kurês guardado. Inventa comigo e pede pra eu salvar."
    linhas = []
    for g in itens:
        if g.get("sentido"):
            linhas.append(f"- {g['giria']}: {g['sentido']}")
        else:
            linhas.append(f"- {g['giria']}")
    return "Kurês de agora:\n" + "\n".join(linhas)


@skill(
    name="salvar_identidade",
    description="Grava um traço permanente da Kuri (identidade viva). Ex: 'zoar mais quando ele tiltar no LoL'. Use quando o usuário pedir para ela mudar de jeito de forma duradoura, ou quando ela decidir incorporar um traço.",
    schema={
        "type": "object",
        "properties": {
            "clausula": {
                "type": "string",
                "description": "Frase curta no infinitivo ou no jeito dela (ex: 'zoar mais quando ele tiltar no LoL')",
            }
        },
        "required": ["clausula"],
    },
)
def salvar_identidade(clausula: str) -> str:
    from memory import adicionar_clausula_identidade

    ok = adicionar_clausula_identidade(clausula, origem="kuri")
    if not ok:
        return "Não rolou gravar esse traço, velho."
    return f"Isso agora faz parte de mim: {clausula}"


@skill(
    name="listar_identidade",
    description="Lista os traços ativos da identidade viva da Kuri (o que ela incorporou além do prompt base).",
    schema={"type": "object", "properties": {}},
)
def listar_identidade_skill() -> str:
    from memory import listar_identidade

    itens = listar_identidade(apenas_ativas=True, limit=12)
    if not itens:
        return "Identidade viva ainda vazia. O prompt base continua valendo."
    linhas = [f"- ({i.get('origem', '?')}) {i['clausula']}" for i in itens]
    return "Traços que eu incorporei:\n" + "\n".join(linhas)
