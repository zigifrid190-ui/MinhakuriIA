import sys
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import asyncio
from stt import ouvir
from tts import falar
from brain import pensar

BANNER = """
======================================================
          KURI IA  -  Jarvis Mode
                                                  
   Sua assistente gamer, cafeinada e sarcastica   
   Fale no microfone ou digite para conversar     
                                                  
   Comandos:                                      
     [Enter]      -> Ouvir pelo microfone         
     [texto]      -> Digitar mensagem             
     "sair"       -> Encerrar                     
     "modo voz"   -> Apenas microfone             
     "modo texto" -> Apenas teclado               
======================================================
"""

MODO_VOZ = "voz"
MODO_TEXTO = "texto"
MODO_HIBRIDO = "hibrido"

def _is_wake_word(texto: str) -> bool:
    """Verifica se o texto contém a wake word (Kuri) no início."""
    if not texto:
        return False
    import re
    texto_limpo = re.sub(r'[^a-z0-9\s]', '', texto.lower().strip())
    palavras = texto_limpo.split()
    if palavras:
        if any(w in ["kuri", "curi", "curie"] for w in palavras[:3]):
            return True
    return False


async def processar_mensagem(texto: str):
    """Envia texto para o cerebro da Kuri e reproduz a resposta."""
    if not texto.strip():
        return

    print(f"\n[VOCE] {texto}")
    print("[BRAIN] Kuri pensando...")

    resultado = await pensar(texto)
    resposta = resultado["resposta"]
    acao = resultado.get("acao_executada")

    print(f"[KURI] {resposta}")
    if acao:
        print(f"[ACAO] {acao}")

    await falar(resposta)


async def loop_hibrido():
    """Modo principal: digite texto ou pressione Enter para usar microfone."""
    # Health check (Fase 1)
    try:
        from health_check import check_environment
        health = check_environment()
        if not health.get("ok"):
            print("[HEALTH] Avisos:", health.get("warnings"))
    except Exception:
        pass

    print(BANNER)
    print("[OK] Kuri ativa! Pressione Enter para falar ou digite uma mensagem.\n")

    # Mensagem de boas-vindas
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
                # Modo microfone
                texto = ouvir()
                if not texto:
                    import routines

                    proativo = await routines.check_proactivity()
                    if proativo:
                        texto = proativo
                        print("\n[ROUTINE] Kuri iniciou uma conversa proativa...")
                    else:
                        print("[!] Não captei nada. Tenta de novo.")
                        continue
                else:
                    if not _is_wake_word(texto):
                        print(f"[WAKE WORD] Ignorado (não chamou a Kuri): '{texto}'")
                        continue
            else:
                texto = entrada

            await processar_mensagem(texto)

        except KeyboardInterrupt:
            print("\n\n[BYE] Kuri encerrada. Ate mais, velho!")
            break
        except Exception as e:
            print(f"[ERRO] {e}")


async def loop_voz():
    """Modo continuo de voz -- fica ouvindo e respondendo sem parar."""
    print(
        "\n[MIC] Modo voz continuo ativado! Fale a qualquer momento. Diga 'sair' para voltar.\n"
    )

    while True:
        try:
            texto = ouvir()
            if not texto:
                continue

            if not _is_wake_word(texto):
                # No modo voz contínuo também filtramos
                print(f"[WAKE WORD] Ignorado: '{texto}'")
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
