"""CLI da Kuri. O cérebro e a fala passam por kuri_runtime (o mesmo do widget)."""

import sys
import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import asyncio
import time as _time

from stt import ouvir
from tts import falar
from config import MAX_CONSECUTIVE_SILENCE, SLEEP_LISTEN_INTERVAL
from kuri_runtime import (
    is_wake_word,
    open_conversation,
    conversation_open,
    process_utterance,
)

BANNER = """
======================================================
          KURI IA  -  presenca no desktop
                                                  
   Cafeinada, sarcastica, na sua mesa             
   Fale no microfone ou digite para conversar     
                                                  
   Comandos:                                      
     [Enter]      -> Ouvir pelo microfone         
     [texto]      -> Digitar mensagem             
     "sair"       -> Encerrar                     
     "modo voz"   -> Apenas microfone             
     "modo texto" -> Apenas teclado               
======================================================
"""

_in_sleep = False
_consecutive_silence = 0


async def processar_mensagem(texto: str):
    """Mesmo caminho do widget: stream + tools + TTS."""
    if not texto.strip():
        return

    global _in_sleep, _consecutive_silence
    if _in_sleep:
        _in_sleep = False
        _consecutive_silence = 0
        print("[Acordando do sono]")

    open_conversation()
    print(f"\n[VOCE] {texto}")
    print("[BRAIN] Kuri pensando...")

    resultado = await process_utterance(texto)
    resposta = resultado.get("resposta_completa") or resultado.get("resposta") or ""
    acao = resultado.get("acao_executada")

    print(f"[KURI] {resposta}")
    if acao:
        print(f"[ACAO] {acao}")


async def loop_hibrido():
    global _in_sleep, _consecutive_silence
    try:
        from health_check import check_environment
        health = check_environment()
        if not health.get("ok"):
            print("[HEALTH] Avisos:", health.get("warnings"))
    except Exception:
        pass

    print(BANNER)
    print("[OK] Kuri ativa! Pressione Enter para falar ou digite uma mensagem.\n")
    await falar("E ai velho, to online! Me diz ai o que tu precisa.")

    while True:
        try:
            entrada = input(
                "\n>> [Enter = mic | texto + Enter = enviar | 'sair' = sair]: "
            ).strip()

            if entrada.lower() in ("sair", "exit", "quit", "q"):
                print("\n[KURI] Falou velho, vai la ser produtivo... ou nao.")
                await falar("Falou velho, vai la ser produtivo... ou nao.")
                break

            if entrada.lower() == "modo voz":
                await loop_voz()
                continue

            if entrada.lower() == "modo texto":
                print("[OK] Modo texto ativado. Digite suas mensagens.")
                continue

            if entrada == "":
                if _in_sleep:
                    _time.sleep(SLEEP_LISTEN_INTERVAL)
                    continue

                texto = ouvir()
                if not texto:
                    _consecutive_silence += 1
                    if _consecutive_silence > MAX_CONSECUTIVE_SILENCE:
                        _in_sleep = True
                        _consecutive_silence = 0
                        print("[Modo sono] Diga 'acorda Kuri' para acordar.")
                        continue

                    import routines
                    proativo = await routines.check_proactivity()
                    if proativo:
                        texto = proativo
                        print("\n[ROUTINE] Kuri iniciou uma conversa proativa...")
                    else:
                        print("[!] Não captei nada. Tenta de novo.")
                        continue
                else:
                    _consecutive_silence = 0
                    if not is_wake_word(texto) and not conversation_open():
                        print(f"[ATENCAO] Fora da conversa. Chama ela pelo nome: '{texto}'")
                        continue
            else:
                texto = entrada
                _consecutive_silence = 0

            await processar_mensagem(texto)

        except KeyboardInterrupt:
            print("\n\n[BYE] Kuri encerrada. Ate mais, velho!")
            break
        except Exception as e:
            print(f"[ERRO] {e}")


async def loop_voz():
    global _in_sleep, _consecutive_silence
    print("\n[MIC] Modo voz continuo. Diga 'sair' para voltar.\n")

    while True:
        try:
            if _in_sleep:
                _time.sleep(SLEEP_LISTEN_INTERVAL)
                continue

            texto = ouvir()
            if not texto:
                _consecutive_silence += 1
                if _consecutive_silence > MAX_CONSECUTIVE_SILENCE:
                    _in_sleep = True
                    _consecutive_silence = 0
                    print("[Modo sono] Diga 'acorda Kuri'.")
                    continue
                continue

            _consecutive_silence = 0

            if not is_wake_word(texto) and not conversation_open():
                print(f"[ATENCAO] Fora da conversa. Chama ela pelo nome: '{texto}'")
                continue

            if texto.lower().strip() in ("sair", "exit", "parar", "para"):
                print("[<<] Voltando ao modo hibrido...")
                break

            await processar_mensagem(texto)

        except KeyboardInterrupt:
            print("\n[<<] Voltando ao modo hibrido...")
            break
        except Exception as e:
            print(f"[ERRO] Modo voz: {e}")


def main():
    try:
        asyncio.run(loop_hibrido())
    except KeyboardInterrupt:
        print("\n[BYE] Encerrado.")
    finally:
        sys.exit(0)


if __name__ == "__main__":
    main()
