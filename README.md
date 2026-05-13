# 🤖 Kuri IA — Seu Assistente Desktop Pessoal (Jarvis Mode)

![Status](https://img.shields.io/badge/Status-v0.5_Desktop_Assistant-green?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-darkblue?style=for-the-badge)
![Privacidade](https://img.shields.io/badge/Privacidade-Local__First-orange?style=for-the-badge)

A **Kuri** é uma assistente virtual autônoma projetada para viver diretamente no seu desktop Windows. Inspirada na filosofia de um "Jarvis pessoal com alma", ela combina inteligência artificial avançada (Grok/Ollama) com uma interface visual viva (Gamer HUD minimalista), permitindo interações rápidas por voz enquanto executa tarefas de forma integrada no seu sistema operacional.

---

## 🌟 O que a Kuri faz hoje (v0.5)

A Kuri evoluiu de um simples chatbot para uma aplicação desktop nativa ultrarrápida:

- **🎙️ Ciclo de Voz Otimizado:** Transcrição instantânea via `faster-whisper` (local-first com filtro VAD e detecção de silêncio de 1.0s) garantindo que seus dados de áudio não sejam enviados para a nuvem.
- **🔊 Voz Premium com Cache:** Integração nativa com a voz profissional da **ElevenLabs** (com sistema de cache local em `tts_cache/` para economizar créditos) e fallback automático para `edge-tts` gratuito.
- **🧠 Cérebro Inteligente (Brain):** Conectada ao Grok-4 (xAI) com **Function Calling**, permitindo à Kuri decidir autonomamente quando conversar ou quando executar comandos no seu PC.
- **🖥️ Controle do Sistema:** Possui 8 ações nativas cadastradas para abrir/fechar apps, fazer pesquisas na web, consultar hora/data, criar/abrir pastas do sistema, tirar prints e controlar o volume do Windows em tempo real.
- **✨ Interface Viva (Gamer HUD):** Janela flutuante desenvolvida em **PyQt6** (260x320, sem bordas, always-on-top e arrastável) com um sistema de avatares em vídeo MP4 em loop nativo que reagem dinamicamente a 5 estados emocionais mapeados pelo LLM (`neutral`, `cool`, `surprised`, `blushing`, `angry`).

---

## 🚀 Como Usar

### Pré-requisitos
- Windows 10/11
- Python 3.10 ou superior
- Microfone e alto-falantes configurados

### Instalação (Modo Desenvolvimento)
1. Clone este repositório:
   ```bash
   git clone https://github.com/teu-usuario/MinhakuriIA.git
   cd MinhakuriIA
   ```
2. Crie e ative o ambiente virtual:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Crie um arquivo `.env` na raiz baseado no exemplo e insira suas credenciais:
   ```env
   GROK_API_KEY=sua_chave_grok
   ELEVENLABS_API_KEY=sua_chave_elevenlabs
   ELEVENLABS_VOICE_ID=id_da_voz_escolhida
   USE_PREMIUM_TTS=true
   ```
5. Inicie a assistente:
   ```bash
   python kuri_desktop.py
   ```

### Usando o Executável Compilado (.exe)
1. Acesse a pasta `dist/KuriIA/`.
2. Execute `KuriIA.exe`.
3. Clique no ícone de engrenagem ⚙️ na barra inferior do widget para configurar seus dispositivos de entrada/saída de áudio, ajustar volume ou alternar entre o TTS Premium e Gratuito.

---

## 🗺️ Roadmap de Evolução (v2.0+)

O desenvolvimento da Kuri segue uma filosofia inspirada na arquitetura **PAI (Personal AI Infrastructure)** de Daniel Miessler, focando em transformá-la em um verdadeiro sistema operacional pessoal inteligente. 

Para ver todos os detalhes técnicos, tarefas e checklists de cada etapa, consulte nosso documento oficial: **[KURI_ROADMAP.md](./KURI_ROADMAP.md)**.

### Resumo dos Sprints:
- **Sprint 1 (Atual): Performance e Voz** — Concluída a integração com ElevenLabs, cache local, otimização de latência do Whisper e responsividade da GUI. *(Pendente otimização de consumo de RAM/CPU para hardware modesto).*
- **Sprint 2: Inteligência e Memória** — Migração da memória JSON para **SQLite** com resumos automáticos de contexto, busca semântica, calibração automática de microfone e suporte nativo ao Python 3.12+.
- **Sprint 3: Visual Premium e Rotinas** — Redesign da interface (300x400 com gradientes, bordas com glow responsivo e transições suaves), além de um motor autônomo de lembretes, tarefas e rotinas.
- **Sprint 4: Inteligência Autônoma** — Implementação do **The Algorithm (7 Fases)** do PAI (`OBSERVE → THINK → PLAN → BUILD → EXECUTE → VERIFY → LEARN`), loop de auto-melhoria contínua e encadeamento de múltiplas ações.
- **Sprint 5: Integrações Externas** — Módulos modulares de monitoramento proativo de redes sociais (YouTube, Twitter/X, Reddit, Discord) e apoio integrado a projetos de código (Git status, resumos de repositórios).
- **Sprint 6: Jarvis Completo** — Fallback offline-first nativo via **Ollama** (Llama 3 / Qwen 2.5) em caso de queda de internet, visão computacional da tela e **Área de Trabalho Remota** segura (FastAPI + WebSockets + 2FA) para controlar o PC via smartphone.

---

## 🔒 Privacidade e Licença

A Kuri foi construída com a privacidade como prioridade fundamental. A detecção de voz e o processamento de áudio local rodam estritamente na sua máquina. O histórico de interações e o perfil de personalidade são salvos localmente em arquivos JSON/SQLite e nunca são compartilhados ou vendidos.

---
*Forjado no Olimpo para ser a assistente definitiva do teu setup.*
