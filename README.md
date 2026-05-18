# 🤖 Kuri IA — Seu Assistente Desktop Pessoal (Jarvis Mode)

![Status](https://img.shields.io/badge/Status-v1.2_Cognitive_Update-blue?style=for-the-badge)
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
- **🖥️ Controle do Sistema:** Possui ações nativas cadastradas para abrir/fechar apps, fazer pesquisas na web, consultar hora/data, criar/abrir pastas do sistema, tirar prints e controlar o volume do Windows em tempo real.
- **🔌 Framework de Skills Dinâmicas & Hooks (NOVO):** Arquitetura totalmente desacoplada sob `kuri_skills/` permitindo carregar, atualizar e adicionar novas habilidades (ações) em tempo de execução via comando de voz (`recarregar_skills`). Possui ganchos (Hooks) integrados para logar e persistir cada ação de forma auditável no SQLite para aprendizado contínuo.
- **✨ Interface Viva (Gamer HUD):** Janela flutuante desenvolvida em **PyQt6** com avatares que reagem dinamicamente a 5 estados emocionais mapeados pelo LLM.
- **🧠 Upgrades Cognitivos (NOVO):**
    - **Consciência Temporal:** Ela agora entende o momento do dia (manhã, tarde, noite, madrugada) e adapta seu comportamento.
    - **Prosódia Emocional:** A voz da Kuri muda de tom, velocidade e estilo dependendo da emoção detectada.
    - **Micro-Proatividade:** Motor de rotinas que permite à Kuri quebrar o silêncio e interagir espontaneamente com você.
    - **Memória de Longo Prazo:** Migração total para **SQLite** com busca por relevância e resumos automáticos de sessões para um contexto infinito.

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
- **Sprint 1: Performance e Voz** — ✅ CONCLUÍDO. Integração ElevenLabs, cache local e latência otimizada.
- **Sprint 2: Inteligência e Memória** — ✅ CONCLUÍDO. SQLite, resumos automáticos, busca por relevância, calibração de microfone e aprendizado ativo de perfil.
- **Sprint 3: Visual Premium e Rotinas** — ✅ CONCLUÍDO. Redesign completo (gradientes, glow, modo compacto) e motor de rotinas proativo 100% ativo.
- **Sprint 4: Inteligência Autônoma** — ✅ CONCLUÍDO. Implementação do algoritmo PAI completo (`OBSERVE → THINK → PLAN → BUILD → EXECUTE → VERIFY → LEARN`), loop de auto-melhoria contínua, encadeamento de múltiplas ações (tool chains), metaprogramação e suíte de testes de resiliência integrada (36 testes).
- **Sprint 5: Integrações Externas** — 🟡 EM PROGRESSO. Módulos de apoio a projetos do Antigravity (Git status, commits) e monitoramento social proativo.
- **Sprint 6: Jarvis Completo** — Fallback offline-first nativo via **Ollama** (Llama 3 / Qwen 2.5) em caso de queda de internet, visão computacional da tela e **Área de Trabalho Remota** segura (FastAPI + WebSockets + 2FA) para controlar o PC via smartphone.

---

## 🔒 Privacidade e Licença

A Kuri foi construída com a privacidade como prioridade fundamental. A detecção de voz e o processamento de áudio local rodam estritamente na sua máquina. O histórico de interações e o perfil de personalidade são salvos localmente em arquivos JSON/SQLite e nunca são compartilhados ou vendidos.

---
*Forjado no Olimpo para ser a assistente definitiva do teu setup.*
