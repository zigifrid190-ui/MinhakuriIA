from stt import ouvir


def main():
    print("Testando STT (Speech-to-Text)...")
    print("Por favor, fale algo no microfone após a mensagem de 'Ouvindo...'")
    texto = ouvir()
    if texto:
        print(f"Texto reconhecido: {texto}")
    else:
        print("Nenhum texto foi reconhecido.")


if __name__ == "__main__":
    main()
