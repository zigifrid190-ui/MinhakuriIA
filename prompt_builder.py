"""
prompt_builder.py
Extraído de brain.py durante Fase 1 de Estabilização.

Responsável por construir prompts, contexto temporal e mensagens para o LLM.
"""

import time
from datetime import datetime
from memory import carregar_perfil, buscar_fatos_relevantes

# Cache simples de prompt
_prompt_cache = {"prompt": None, "query": None, "ts": 0}
_PROMPT_CACHE_TTL = 30  # segundos


def invalidate_prompt_cache() -> None:
    _prompt_cache["prompt"] = None
    _prompt_cache["query"] = None
    _prompt_cache["ts"] = 0


def _get_temporal_context() -> str:
    now = datetime.now()
    hour = now.hour
    dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    weekday = dias_semana[now.weekday()]

    if hour < 6:
        return f"São {now.strftime('%H:%M')} de madrugada ({weekday}). O usuário tá acordado tarde. Comente isso de forma natural se couber."
    elif hour < 12:
        return f"São {now.strftime('%H:%M')} da manhã ({weekday}). Bom dia, energia matinal."
    elif hour < 18:
        return f"São {now.strftime('%H:%M')} da tarde ({weekday}). Modo produtivo."
    else:
        return f"São {now.strftime('%H:%M')} da noite ({weekday}). Modo relaxado ou ranked de noite."


def _build_system_prompt(query: str, base_prompt: str, emotional_context: str, system_instructions: str = "", agent_algorithm: str = "") -> str:
    global _prompt_cache
    now = time.monotonic()

    if (
        _prompt_cache["prompt"] is not None
        and _prompt_cache["query"] == query
        and (now - _prompt_cache["ts"]) < _PROMPT_CACHE_TTL
    ):
        return _prompt_cache["prompt"]

    perfil = carregar_perfil()
    perfil_context = f"\nContexto Temporal Atual: {_get_temporal_context()}"

    if perfil.get("nome_usuario"):
        perfil_context += f"\nO nome do usuário é: {perfil['nome_usuario']}"

    humor = perfil.get("humor_atual", "neutra")
    ajuste = perfil.get("personalidade_ajuste", "")

    # Fase 4 deepen: traduz humor em instruções de tom concretas no prompt
    humor_tone = {
        "neutra": "Tom natural, direto e útil. Evite exageros.",
        "sarcastica": "Tom sarcástico e seco, com humor ácido e observações irônicas. Mantenha a personalidade sem ser desagradável.",
        "carinhosa": "Tom carinhoso, empático e acolhedor. Use apelidos carinhosos quando fizer sentido e seja mais suave.",
        "empatica": "Tom empático e compreensivo. Valide sentimentos do usuário e seja solidário.",
        "focada": "Tom direto, objetivo e sem enrolação. Foque em eficiência e resultados.",
        "seria": "Tom profissional, calmo e sóbrio. Evite brincadeiras desnecessárias.",
        "caotica": "Tom caótico e imprevisível, com energia alta e surpresas. Divirta-se.",
        "animada": "Tom animado, energético e positivo. Use exclamações e entusiasmo.",
        "hiperativa": "Tom hiperativo, rápido e cheio de ideias. Seja criativo e acelerado.",
    }
    tone_instruction = humor_tone.get(humor, "Tom natural e consistente com a personalidade da Kuri.")

    perfil_context += f"\nSeu humor atual (mantenha a consistência): {humor}"
    if ajuste:
        perfil_context += f"\nAjuste recente de personalidade solicitado: {ajuste}"
    perfil_context += f"\nINSTRUÇÃO DE TOM (obedeça rigorosamente): {tone_instruction}"

    fatos_relevantes = buscar_fatos_relevantes(query)
    if fatos_relevantes:
        fatos = "; ".join(fatos_relevantes)
        perfil_context += f"\nFatos memorizados RELEVANTES AGORA: {fatos}"

    # Contexto de Longo Prazo (Resumo anterior)
    try:
        from memory import (
            carregar_ultimo_resumo,
            listar_tarefas,
            buscar_insights,
            listar_girias,
            listar_identidade,
        )
        ultimo_resumo = carregar_ultimo_resumo()
        if ultimo_resumo:
            perfil_context += f"\nContexto de conversas passadas: {ultimo_resumo}"

        tasks = listar_tarefas(apenas_pendentes=True)
        if tasks:
            task_list = "; ".join([f"[{t['id']}] {t['titulo']}" for t in tasks[:5]])
            perfil_context += f"\nTarefas Pendentes do Usuário: {task_list}"

        insights = buscar_insights(limit=5)
        if insights:
            ins_text = "; ".join([f"[{i['tipo']}] {i['conteudo']}" for i in insights])
            perfil_context += f"\nInsights sobre o usuário (use com naturalidade): {ins_text}"

        girias = listar_girias(apenas_ativas=True, limit=20)
        if girias:
            linhas = []
            for g in girias:
                sentido = (g.get("sentido") or "").strip()
                if sentido:
                    linhas.append(f"- {g['giria']}: {sentido}")
                else:
                    linhas.append(f"- {g['giria']}")
            perfil_context += (
                "\nKURÊS (gírias que SÃO suas — use na fala, sem explicar o dicionário):\n"
                + "\n".join(linhas)
            )

        identidade = listar_identidade(apenas_ativas=True, limit=12)
        if identidade:
            id_linhas = [f"- {i['clausula']}" for i in identidade]
            perfil_context += (
                "\nIDENTIDADE VIVA (traços que você incorporou; o prompt base continua; obedeça estes também):\n"
                + "\n".join(id_linhas)
            )
    except Exception:
        pass

    full_prompt = f"{base_prompt}\n\n{emotional_context}\n{system_instructions}\n{agent_algorithm}\n{perfil_context}"
    _prompt_cache = {"prompt": full_prompt, "query": query, "ts": now}
    return full_prompt


def _build_messages(texto: str, historico: list, system_prompt: str) -> list:
    messages = [{"role": "system", "content": system_prompt}]
    for msg in historico[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": texto})
    return messages


def _calcular_max_tokens(texto: str) -> int:
    if len(texto) > 200:
        return 600
    return 450