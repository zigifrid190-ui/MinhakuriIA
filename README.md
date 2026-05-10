# 🤖 Kuri IA - Seu Assistente Desktop Pessoal

![Kuri Header](https://img.shields.io/badge/Status-Desenvolvimento_Ativo-green?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-darkblue?style=for-the-badge)

A **Kuri** é um assistente virtual autônomo projetado para viver diretamente no seu desktop. Inspirada na ideia de um "Jarvis pessoal", ela combina inteligência artificial avançada com uma interface visual minimalista e funcional (Widget), permitindo interações naturais por voz enquanto executa tarefas no seu computador.

---

## 🌟 Inspiração e Visão
O projeto nasceu do desejo de tirar a IA de dentro do navegador e trazê-la para o ambiente onde o trabalho real acontece: o sistema operacional. 

As principais inspirações foram:
- **J.A.R.V.I.S. (Homem de Ferro):** A ideia de um assistente onipresente que entende o contexto do seu computador.
- **Mascotes Virtuais:** Trazer uma identidade visual (avatar animado) para criar uma conexão mais humana e menos "robótica".
- **Automação Pragmática:** Uma ferramenta que não apenas conversa, mas que *faz* coisas (abrir apps, controlar volume, gerenciar arquivos).

---

## 🚀 O Processo de Criação
A Kuri evoluiu de um simples bot de API para uma aplicação desktop robusta:

1.  **Core de Voz:** Implementamos um loop de voz-para-voz usando `faster-whisper` (STT local) para privacidade e velocidade, e `edge-tts` para vozes naturais e leves.
2.  **O Cérebro (Brain):** Integrada ao Grok (xAI) para uma personalidade sarcástica, brasileira e eficiente, capaz de decidir quando usar ferramentas do sistema.
3.  **Interface (HUD):** Desenvolvida em **PyQt6**, a interface foi desenhada no estilo "Gamer HUD", sendo pequena, arrastável e "always-on-top".
4.  **Integração Visual:** Criamos um sistema de estados emocionais que mapeia a resposta do LLM para animações específicas do avatar em tempo real.

---

## 🛠️ Como Usar

### Pré-requisitos
- Python 3.10 ou superior.
- Microfone e Saída de Áudio configurados.

### Instalação (Desenvolvimento)
1.  Clone o repositório.
2.  Crie um ambiente virtual: `python -m venv venv`.
3.  Instale as dependências: `pip install -r requirements.txt`.
4.  Configure seu arquivo `.env` com as chaves necessárias (Grok API).
5.  Execute: `python kuri_desktop.py`.

### Usando o Executável
Se você compilou o projeto usando o PyInstaller:
1.  Vá até `dist/KuriIA/`.
2.  Execute o `KuriIA.exe`.
3.  Ajuste as configurações de áudio no ícone de engrenagem ⚙️ no widget.

---

## 🔮 Próximos Passos (Roadmap)
A Kuri está em constante evolução. Os planos futuros incluem:

- [ ] **Área de Trabalho Remota:** Capacidade de visualizar e interagir com o desktop remotamente via comandos de voz.
- [ ] **Visão Computacional:** Permitir que a Kuri "veja" o que está na sua tela para ajudar em tarefas visuais ou depuração de código.
- [ ] **Memória de Longo Prazo:** Um sistema de banco de dados vetorial para ela lembrar de fatos complexos por meses.
- [ ] **Integração com Casa Inteligente:** Controlar luzes e dispositivos IoT diretamente pelo widget.

---

## 📜 Licença e Privacidade
Este é um projeto privado. Todos os dados de voz são processados localmente ou via API segura, e o histórico de conversas permanece apenas na sua máquina.

---
*Criado com ❤️ para ser o melhor assistente que um dev pode ter.*
