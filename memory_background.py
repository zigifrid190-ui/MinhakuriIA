"""
memory_background.py

Extraído durante Fase 1 - Estabilização.

Funções que rodam em background para gerenciar memória, insights e auto-avaliação da Kuri.
"""

import asyncio
import json
import re as _re

import httpx

from config import (
    GROK_API_KEY, GROK_MODEL, GROK_URL, CONTEXT_WINDOW,
    RESUMO_INTERVALO, INSIGHTS_INTERVALO, AUTO_AVALIACAO_INTERVALO
)
from logger import get_logger
from memory import (
    salvar_resumo,
    adicionar_insight,
    atualizar_perfil,
    adicionar_clausula_identidade,
)

log = get_logger("memory_background")


async def _gerar_resumo_background(historico: list):
    """Gera um resumo da conversa atual em segundo plano."""
    try:
        log.info("Gerando resumo automático da sessão...")
        mensagens_texto = "\n".join(
            [f"{m['role']}: {m['content']}" for m in historico[-CONTEXT_WINDOW:]]
        )

        prompt_resumo = (
            "Resuma os pontos principais desta conversa entre a Kuri (IA) e o Usuário em 3 tópicos curtos e diretos. "
            "Foque em fatos aprendidos, decisões tomadas ou o clima da conversa.\n\n"
            f"Conversa:\n{mensagens_texto}"
        )

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                GROK_URL,
                headers={"Authorization": f"Bearer {GROK_API_KEY}"},
                json={
                    "model": GROK_MODEL,
                    "messages": [
                        {"role": "system", "content": "Você é um assistente de memória. Seja conciso."},
                        {"role": "user", "content": prompt_resumo},
                    ],
                    "max_tokens": 150,
                },
            )
            response.raise_for_status()
            resumo = response.json()["choices"][0]["message"]["content"].strip()
            salvar_resumo(resumo)
            log.info("Resumo salvo com sucesso!")
    except Exception as e:
        log.error(f"Falha ao gerar resumo: {e}")


async def _extrair_insights_background(historico: list):
    """Extrai insights comportamentais do usuário."""
    try:
        log.info("Extraindo insights comportamentais...")
        mensagens_texto = "\n".join(
            [f"{m['role']}: {m['content']}" for m in historico[-CONTEXT_WINDOW:]]
        )

        prompt_insights = (
            "Analise esta conversa entre a Kuri (IA) e o Usuário. "
            "Extraia NO MÁXIMO 3 insights sobre o usuário. "
            "Cada insight deve ter o formato JSON:\n"
            '[{"tipo": "preferencia|habito|estilo|assunto", "conteudo": "descrição curta", "confianca": 0.5}]\n'
            "Retorne APENAS o JSON array, sem texto extra.\n\n"
            f"Conversa:\n{mensagens_texto}"
        )

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                GROK_URL,
                headers={"Authorization": f"Bearer {GROK_API_KEY}"},
                json={
                    "model": GROK_MODEL,
                    "messages": [
                        {"role": "system", "content": "Você é um analisador de comportamento. Retorne apenas JSON."},
                        {"role": "user", "content": prompt_insights},
                    ],
                    "max_tokens": 200,
                },
            )
            response.raise_for_status()
            raw = response.json()["choices"][0]["message"]["content"].strip()

            match = _re.search(r"\[.*\]", raw, flags=_re.DOTALL)
            if match:
                insights = json.loads(match.group())
                for ins in insights:
                    adicionar_insight(
                        tipo=ins.get("tipo", "assunto"),
                        conteudo=ins.get("conteudo", ""),
                        confianca=float(ins.get("confianca", 0.5)),
                    )
                log.info(f"{len(insights)} insight(s) extraído(s) e salvo(s).")
    except Exception as e:
        log.error(f"Falha ao extrair insights: {e}")


async def _auto_avaliar_kuri_background(historico: list):
    """Realiza auto-avaliação autônoma da Kuri."""
    try:
        log.info("Iniciando auto-avaliação comportamental da Kuri...")
        mensagens_texto = "\n".join(
            [f"{m['role']}: {m['content']}" for m in historico[-50:]]
        )

        prompt_avaliacao = (
            "Analise as últimas 50 interações da Kuri (IA) com o Usuário.\n"
            "Gere JSON com:\n"
            '- "satisfacao_usuario": número 0 a 1\n'
            '- "clausulas_identidade": até 2 frases CURTAS no infinitivo que a Kuri deve incorporar '
            '(ex: "zoar mais quando ele tiltar no LoL"). Só traços estáveis, não humor de um turno.\n'
            "Retorne APENAS o JSON.\n\n"
            f"Histórico:\n{mensagens_texto}"
        )

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                GROK_URL,
                headers={"Authorization": f"Bearer {GROK_API_KEY}"},
                json={
                    "model": GROK_MODEL,
                    "messages": [
                        {"role": "system", "content": "Você é um auditor de IA. Retorne apenas JSON válido."},
                        {"role": "user", "content": prompt_avaliacao},
                    ],
                    "max_tokens": 400,
                },
            )
            response.raise_for_status()
            raw = response.json()["choices"][0]["message"]["content"].strip()

            match = _re.search(r"\{.*\}", raw, flags=_re.DOTALL)
            if match:
                avaliacao_json = match.group()
                atualizar_perfil("auto_avaliacao_recente", avaliacao_json)
                try:
                    data = json.loads(avaliacao_json)
                    for clausula in (data.get("clausulas_identidade") or [])[:2]:
                        if isinstance(clausula, str) and clausula.strip():
                            adicionar_clausula_identidade(clausula.strip(), origem="auto")
                except Exception as parse_err:
                    log.warning(f"Auto-avaliação JSON ok, cláusulas não aplicadas: {parse_err}")
                log.info("Auto-avaliação salva na identidade viva.")
    except Exception as e:
        log.error(f"Falha na auto-avaliação: {e}")
