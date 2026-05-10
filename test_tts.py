import asyncio
from tts import falar

async def main():
    print("Testando o TTS (Text-to-Speech)...")
    await falar("Oi, este é um teste do sistema de voz da Kuri. Se você está me ouvindo, o áudio está funcionando!")
    print("Teste finalizado.")

if __name__ == "__main__":
    asyncio.run(main())
