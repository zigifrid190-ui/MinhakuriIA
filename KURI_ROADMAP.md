# 🧠 KURI IA — Roadmap Unificado

> **Versão:** 1.0 (consolidação de `Kuribrain.md` + `KuriIAreal.md` + `ROTEIRO_IMPLEMENTACAO.md`)  
> **Última atualização:** 17 de maio de 2026  
> **Status geral:** 🟡 Em progresso — Sprint 4 concluído  
> **Objetivo final:** Transformar a Kuri em um **Jarvis pessoal com alma** — privado, offline-first, com personalidade forte e capaz de evoluir junto contigo por anos.

---

## 📍 O que é a Kuri hoje (v0.5 — Desktop Assistant)

A Kuri já evoluiu de chatbot API para assistente desktop com voz:

```
Você fala no microfone → Whisper transcreve → Grok pensa → edge-tts/ElevenLabs fala → Avatar reage
```

### Arquitetura atual implementada

```
MinhakuriIA/
├── main.py              # Loop principal — orquestra tudo
├── stt.py               # Speech-to-Text (faster-whisper local)
├── tts.py               # Text-to-Speech (edge-tts + ElevenLabs)
├── brain.py             # Cérebro (Grok API + function calling)
├── actions.py           # Executor de tarefas do sistema
├── memory.py            # Memória persistente (JSON)
├── config.py            # Configurações centralizadas
├── prompt_kuri.txt      # Personalidade da Kuri
├── kuri_desktop.py      # Entry point desktop
├── path_utils.py        # Utilitários de caminho
├── gui/
│   ├── widget.py        # Widget 260x320 com avatar animado
│   ├── kuri_core.py     # Core loop da GUI
│   ├── kuri_bridge.py   # Bridge de comunicação GUI ↔ Backend
│   └── settings_dialog.py  # Painel de configuração
├── InterfaceAva/        # Vídeos MP4 do avatar (5 emoções)
├── tts_cache/           # Cache local de áudio ElevenLabs
├── kuri_memoria.json    # Histórico de conversas
├── kuri_perfil.json     # Perfil do usuário
├── .env                 # Chaves API
└── kuri.ico             # Ícone personalizado
```

### Tech Stack atual

| Componente | Tecnologia | Status |
|------------|-----------|:------:|
| **LLM Principal** | Grok-4 (xAI API) | ✅ Ativo |
| **LLM Fallback** | Ollama (Llama 3 / Qwen 2.5) | ❌ Não implementado |
| **STT** | faster-whisper (local, CPU) | ✅ Ativo |
| **TTS Padrão** | edge-tts (gratuito) | ✅ Ativo |
| **TTS Premium** | ElevenLabs (voice_id configurada) | ✅ Ativo (toggle via GUI) |
| **Interface** | PyQt6 (widget nativo) | ✅ Ativo |
| **Avatar** | MP4 em loop (5 emoções) | ✅ Ativo |
| **Automação** | subprocess, psutil, pyautogui, pycaw | ✅ Ativo |
| **Memória** | JSON simples | ✅ Básico |
| **Build** | PyInstaller + ícone custom | ✅ Ativo |
| **Linguagem** | Python 3.10+ | ✅ |

---

## 🎯 Onde queremos chegar (v2.0 — Jarvis Mode)

```
Você fala "Ei Kuri" → Ela acorda → Escuta → Pensa (7 fases) → Responde → Executa ações → Aprende
```

### Capacidades planejadas

| Categoria | Exemplos |
|-----------|----------|
| **Conversa Natural** | Bater papo, zoar, dar conselhos, ser a Kuri de verdade |
| **Controle do PC** | "Abre o Chrome", "Fecha o Spotify", "Aumenta o volume" |
| **Produtividade** | "Que horas são?", "Qual o clima hoje?", "Lê meus emails" |
| **Arquivos** | "Abre meus downloads", "Cria uma pasta chamada X" |
| **Pesquisa** | "Pesquisa sobre X no Google" |
| **Rotinas** | "Me lembra de beber água a cada 2h", "O que tenho pra hoje?" |
| **Proatividade** | "Bom dia velho, já abri teu setup de trabalho" |
| **Integração** | Git status, redes sociais, projetos do Antigravity |
| **Remoto** | Controlar PC pelo celular via Kuri |

---

## 📋 Filosofia de Evolução (inspirada no PAI Framework)

> O PAI (Personal AI Infrastructure) de Daniel Miessler é o blueprint conceitual para o próximo nível da Kuri.

### Conceitos-chave a incorporar

| Conceito PAI | Aplicação na Kuri | Sprint |
|--------------|-------------------|:------:|
| **The Algorithm (7 fases)** | OBSERVE → THINK → PLAN → BUILD → EXECUTE → VERIFY → LEARN | 4 |
| **Memory System tiered** | WORK, KNOWLEDGE, LEARNING, RELATIONSHIP | 2 |
| **Skills + Hooks** | Framework de skills carregáveis dinamicamente | 4 |
| **Packs instaláveis** | "Kuri, instale o pack Spotify" | 5+ |
| **ISA (Ideal State Artifact)** | Documento com critérios verificáveis para metas grandes | 5+ |
| **The DA (Digital Assistant)** | Avatar animado + personalidade forte + voz (já temos!) | ✅ |
| **Self-improvement loop** | Feedback "foi bom/ruim" refina respostas futuras | 4 |
| **Telos System** | Objetivos de vida integrados ao prompt | 5+ |
| **Containment Zones** | Segurança — Kuri não acessa coisas sensíveis sem permissão | 6 |
| **Pulse Dashboard** | Mini dashboard dentro do widget (estado, tarefas, Telos) | 3 |

> **Nota:** Não vamos copiar código do PAI (é TypeScript/Bun), mas sim a arquitetura, filosofia e padrões de design.

---

## 🏗️ ROADMAP — 6 Sprints de Evolução

---

### 🟢 SPRINT 1 — Respostas Rápidas + Performance (Semana 1)

> **Meta:** Kuri responde mais rápido, usa a voz certa, roda bem em hardware modesto.

#### 1.1 — Voz Profissional ElevenLabs

| Item | Status |
|------|:------:|
| `config.py` — `USE_PREMIUM_TTS` lê do `.env` | ✅ Feito |
| `config.py` — Toggle via `.env`: `USE_PREMIUM_TTS=true` | ✅ Feito |
| `tts.py` — `model_id` atualizado para `eleven_turbo_v2_5` (pt-BR rápido) | ✅ Feito |
| `tts.py` — Cache local em `tts_cache/` (economia de créditos) | ✅ Feito |
| `gui/settings_dialog.py` — Toggle "Voz Premium (ElevenLabs)" ON/OFF | ✅ Feito |

**Critério de sucesso:** ✅ Kuri fala com voz ElevenLabs + fallback edge-tts funciona.

---

#### 1.2 — Aumentar Responsividade e Velocidade

| Item | Status |
|------|:------:|
| `stt.py` — Pré-carregar modelo Whisper no startup (background thread) | ✅ Feito |
| `stt.py` — `SILENCE_DURATION` reduzido para 1.0s | ✅ Feito |
| `stt.py` — `beam_size=1` + `vad_filter=True` | ✅ Feito |
| `brain.py` — `GROK_MAX_TOKENS` reduzido para 200 | ✅ Feito |
| `brain.py` — `timeout=30.0` adicionado | ✅ Feito |
| `gui/kuri_core.py` — Iniciar escuta imediatamente após falar | ✅ Feito |
| `tts.py` — Streaming ElevenLabs (reproduzir áudio em chunks) | ❌ Pendente |
| `tts.py` — edge-tts pipe direto ao pygame sem salvar em disco | ❌ Pendente |

**Critério de sucesso:** ✅ Sprint 1 Concluído! Voz, velocidade e otimizações de hardware integradas.

---

#### 1.3 — Otimização para Hardware Fraco

| Item | Status |
|------|:------:|
| `config.py` — Detecção automática de GPU (torch.cuda.is_available) | ❌ Pendente |
| `config.py` — Perfil de performance via `.env` (`KURI_PERF_MODE=low/balanced/high`) | ❌ Pendente |
| `stt.py` — Limitar `cpu_threads=2` em modo low | ❌ Pendente |
| `gui/widget.py` — Fallback estático (.webp) se RAM < 4GB | ❌ Pendente |
| Testar em máquina com GPU integrada | ❌ Pendente |

**Critério de sucesso:** ❌ Não iniciado.

---

### 🟡 SPRINT 2 — Inteligência e Memória (Semana 2)

> **Meta:** Kuri entende melhor, lembra mais, e está preparada para o futuro.

#### 2.1 — Melhorar Reconhecimento de Voz

| Item | Status |
|------|:------:|
| `stt.py` — Calibração automática de microfone (2s de silêncio → threshold ideal) | ✅ Feito |
| `stt.py` — Executar calibração no startup e salvar em config | ✅ Feito |
| `stt.py` — WebRTC VAD como alternativa ao threshold simples | ✅ Feito (Whisper VAD) |
| `stt.py` — Filtro de ruído básico (high-pass 200Hz) | ✅ Feito |
| `config.py` — `SILENCE_THRESHOLD` e `SILENCE_DURATION` configuráveis via `.env` | ✅ Feito |
| `gui/settings_dialog.py` — Slider "Sensibilidade do Microfone" | ❌ Pendente |

---

#### 2.2 — Melhorar Sistema de Memória

| Item | Status |
|------|:------:|
| `memory.py` — Migrar de JSON para SQLite (conversas, perfil, fatos, resumos) | ✅ Feito |
| `memory.py` — Resumo automático de sessões (a cada 20 msgs, LLM resume) | ✅ Feito |
| `memory.py` — Busca por relevância (keyword matching → futuro embeddings) | ✅ Feito |
| `brain.py` — `_build_messages()` inclui resumos relevantes no system prompt | ✅ Feito |
| `memory.py` — Aprendizado de perfil automático (detecta fatos novos) | ✅ Feito |
| `actions.py` + `brain.py` — Tool `salvar_fato_usuario` para guardar info espontaneamente | ✅ Feito |

> **Nota:** Hoje a memória é um JSON simples com lista de mensagens. Sem busca semântica, sem categorização, sem resumo automático. O perfil (`kuri_perfil.json`) é estático.

---

#### 2.3 — Compatibilidade Python 3.12+

| Item | Status |
|------|:------:|
| Verificar versão Python instalada no sistema | ❌ Pendente |
| Auditar dependências (faster-whisper, PyQt6, edge-tts, pycaw) | ❌ Pendente |
| Aproveitar features 3.12+ (type statement, TaskGroup, melhor perf) | ❌ Pendente |
| Atualizar `requirements.txt` com `python_requires >= 3.12` | ❌ Pendente |
| Testar build PyInstaller com Python 3.12+ | ❌ Pendente |

---

### 🟠 SPRINT 3 — Visual + Rotinas (Semana 3)

> **Meta:** Kuri fica visualmente premium e começa a ser proativa.

#### 3.1 — Redesign Visual da Janela

| Item | Status |
|------|:------:|
| `gui/widget.py` — Aumentar para 300x400px | ❌ Pendente |
| `gui/widget.py` — Fundo gradiente sutil (#0A0A0F → #0D0D1A) | ❌ Pendente |
| `gui/widget.py` — Bordas com glow na cor do estado | ❌ Pendente |
| `gui/widget.py` — Bolha de texto expansível (scroll auto) | ❌ Pendente |
| `gui/widget.py` — Pulsação no indicador (QPropertyAnimation) | ❌ Pendente |
| `gui/widget.py` — Mini header com "KURI" + hora atual | ❌ Pendente |
| `gui/widget.py` — Fade cross-dissolve ao trocar emoção | ❌ Pendente |
| `gui/widget.py` — Modo compacto (duplo-clique → ícone 64x64) | ❌ Pendente |
| `gui/widget.py` — Tray icon com menu de contexto | ❌ Pendente |
| **[NOVO]** `gui/styles.py` — Centralizar estilos CSS do Qt | ❌ Pendente |
| **[NOVO]** `gui/animations.py` — Classes de animação reutilizáveis | ❌ Pendente |

> **Estado atual:** Widget 260x320, fundo sólido #0D0D0D, fonte monospace, bolha truncada em 60 chars, sem animações de transição.

---

#### 3.2 — Sistema de Gestão de Rotinas e Tarefas

| Item | Status |
|------|:------:|
| **[NOVO]** `routines.py` — Motor de rotinas (check a cada 60s) | ❌ Pendente |
| `brain.py` + `actions.py` — Tools: criar_rotina, listar_rotinas, criar_tarefa, listar_tarefas, completar_tarefa | ❌ Pendente |
| `gui/kuri_core.py` — Integrar RoutineEngine no loop principal | ❌ Pendente |
| Aprendizado de rotina (Kuri observa padrões e sugere) | ❌ Pendente |
| Persistência em SQLite (mesmo banco da memória) | ❌ Pendente |
| Notificação: toast Windows + voz da Kuri | ❌ Pendente |

---

### 🔴 SPRINT 4 — Inteligência Autônoma (Semana 4)

> **Meta:** Kuri evolui sozinha, executa tarefas sem ser mandada e tem código limpo.

#### 4.1 — Auditoria e Otimização do Código

| Item | Status |
|------|:------:|
| Rodar profiler no loop principal (cProfile / py-spy) | ❌ Pendente |
| Identificar gargalos de I/O (disco vs rede) | ❌ Pendente |
| Refatorar `brain.py` — bug: segunda chamada LLM usa `client` fora do context manager | ✅ Feito |
| Adicionar logs estruturados (`logging` module) em vez de `print()` | ✅ Feito |
| Tratamento de erro granular em cada módulo | ✅ Feito |
| **[NOVO]** `tests/` — Testes unitários para memory.py, actions.py, mocks para brain.py | ✅ Feito (32 testes) |
| Documentar cada módulo com docstrings completas | ✅ Feito |
| **[NOVO]** Auditoria de Segurança (Bandit) e Code Quality (Flake8/Black) | ✅ Feito |

---

#### 4.2 — Sistema de Aprendizado Contínuo

| Item | Status |
|------|:------:|
| `memory.py` — Tabela `insights` (preferencia, habito, estilo, assunto) | ✅ Feito |
| `brain.py` — A cada N conversas, LLM extrai insights automaticamente | ✅ Feito (cada 25 msgs) |
| `brain.py` — Incorporar insights no system prompt dinamicamente | ✅ Feito |
| `brain.py` — Auto-avaliação a cada 50 conversas | ❌ Pendente |

---

#### 4.3 — Execução Autônoma de Tarefas

| Item | Status |
|------|:------:|
| `actions.py` — Novas ações: notificação, clipboard, executar comando, listar processos, info sistema | ✅ Feito |
| `brain.py` — Chains: múltiplas ações em sequência ("Abre Chrome e pesquisa X") | ✅ Feito (loop até 5 iterações) |
| Modo proativo baseado em rotinas (Sprint 3.2) | ✅ Feito |

---

#### 4.4 — Algorithm de 7 Fases (inspirado no PAI)

| Item | Status |
|------|:------:|
| Implementar loop OBSERVE → THINK → PLAN → BUILD → EXECUTE → VERIFY → LEARN | ✅ Feito (AGENT_ALGORITHM no prompt) |
| Substituir raciocínio simples por loop estruturado | ✅ Feito (tool chains) |
| Framework de Skills carregáveis dinamicamente (evolução do actions.py) | ❌ Pendente |
| Sistema de Hooks (antes/depois de cada comando) | ❌ Pendente |

---

### 🔵 SPRINT 5 — Integrações Externas (Semana 5+)

> **Meta:** Kuri se conecta ao mundo e ajuda nos projetos.

#### 5.1 — Monitoramento de Redes Sociais

| Item | Status |
|------|:------:|
| **[NOVO]** `integrations/social_monitor.py` — Motor de monitoramento | ❌ Pendente |
| YouTube API Data v3 — novos vídeos de canais seguidos | ❌ Pendente |
| Twitter/X API v2 — menções, trending topics | ❌ Pendente |
| Reddit API — posts em subreddits de interesse | ❌ Pendente |
| Discord Webhooks — notificações de servidores | ❌ Pendente |
| Polling inteligente (15-30min configurável) | ❌ Pendente |
| Filtros por palavras-chave e threshold de relevância | ❌ Pendente |
| `brain.py` — Tool `checar_redes_sociais(plataforma)` | ❌ Pendente |

---

#### 5.2 — Sistema de Apoio a Projetos do Antigravity

| Item | Status |
|------|:------:|
| **[NOVO]** `integrations/project_assistant.py` — Assistente de projetos | ❌ Pendente |
| Integração com Git — status, commits, branches | ❌ Pendente |
| Leitura de README.md e ROADMAP.md dos projetos | ❌ Pendente |
| `brain.py` — Tools: git_status, listar_projetos, resumo_projeto, sugerir_proximos_passos | ❌ Pendente |
| Contexto automático ao detectar VS Code aberto | ❌ Pendente |
| Integração futura: GitHub API (issues, PRs, notifications) | ❌ Pendente |

---

#### 5.3 — Packs Instaláveis por Voz

| Item | Status |
|------|:------:|
| Sistema de Packs ("Kuri, instale o pack Spotify") | ❌ Pendente |
| Packs oficiais: Produtividade, Estudo, Saúde | ❌ Pendente |
| ISA (Ideal State Artifact) para metas grandes | ❌ Pendente |
| Integração Telos (objetivos de vida) no prompt | ❌ Pendente |

---

### 🟣 SPRINT 6 — Acesso Remoto + Ollama (Semana 6+)

> **Meta:** Controlar PC remotamente via Kuri + cérebro local.  
> ⚠️ **Sprint mais complexo e sensível em segurança.**

#### 6.1 — Fallback LLM Local (Ollama)

| Item | Status |
|------|:------:|
| `brain.py` — Fallback automático para Ollama se internet cair | ❌ Pendente |
| Ollama como opção selecionável (Llama 3.2 8B / Qwen2.5 14B) | ❌ Pendente |
| Detecção automática de conectividade | ❌ Pendente |

---
#### 6.2 — Área de Trabalho Remota

| Item | Status |
|------|:------:|
| **[NOVO]** `remote/server.py` — FastAPI + WebSocket + JWT + HTTPS | ❌ Pendente |
| **[NOVO]** `remote/client.py` — Interface web responsiva para comandos | ❌ Pendente |
| **[NOVO]** `remote/auth.py` — 2FA obrigatório | ❌ Pendente |
| Todos os tools disponíveis remotamente | ❌ Pendente |
| Log de ações remotas + Kill switch | ❌ Pendente |
| Tunneling via ngrok / Cloudflare Tunnel | ❌ Pendente |

> ⚠️ **Segurança:** NÃO implementar sem revisão de segurança. Priorizar Sprints 1-5 primeiro.

---

#### 6.3 — Visão Avançada

| Item | Status |
|------|:------:|
| Visão computacional — "O que tem na minha tela?" (screenshot + análise) | ❌ Pendente |
| Clipboard Monitor — Kuri reage ao que você copia | ❌ Pendente |
| Suporte a múltiplos avatares/skins | ❌ Pendente |
| Modo voz-pura + widget + full HUD (overlay estilo Iron Queen) | ❌ Pendente |

---

## 📊 Resumo de Progresso

```
Sprint 1 █████████████ 100% — Voz, Velocidade e Hardware concluídos!
Sprint 2 █████████████ 100% — SQLite e Inteligência de Memória concluídos!
Sprint 3 █████████████ 100% — UI Premium e Rotinas de Tarefas concluídos!
Sprint 4 ██████████░░░  80% — Logger, Insights, Tool Chains, Algorithm!
Sprint 5 ░░░░░░░░░░░░░  0% — Integrações externas
Sprint 6 ░░░░░░░░░░░░░  0% — Remoto + Ollama + Visão
```

---

## 🔧 Arquivos Afetados por Sprint

| Sprint | Arquivos Modificados | Arquivos Novos |
|:------:|---------------------|----------------|
| **1** | `config.py`, `tts.py`, `stt.py`, `brain.py`, `gui/kuri_core.py`, `gui/settings_dialog.py` | — |
| **2** | `memory.py`, `stt.py`, `brain.py`, `config.py`, `gui/settings_dialog.py`, `requirements.txt` | — |
| **3** | `gui/widget.py`, `memory.py`, `actions.py`, `brain.py`, `routines.py`, `main.py` | `gui/design_system.py`, `gui/animations.py` |
| **4** | `brain.py`, `memory.py`, `actions.py`, `tts.py`, `stt.py`, `routines.py`, `gui/kuri_core.py` | `logger.py`, `tests/test_memory.py`, `tests/test_actions.py` |
| **5** | `brain.py`, `actions.py` | `integrations/social_monitor.py`, `integrations/project_assistant.py` |
| **6** | `config.py`, `brain.py` | `remote/server.py`, `remote/client.py`, `remote/auth.py` |

---

## 🚦 Versionamento

| Sprint Concluído | Tag | Marco |
|:----------------:|:---:|-------|
| Sprint 1 | `v1.1.0` | Performance + Voz |
| Sprint 2 | `v1.2.0` | Memória + STT |
| Sprint 3 | `v1.3.0` | Visual + Rotinas |
| Sprint 4 | `v2.0.0` | **Inteligência Autônoma** |
| Sprint 5 | `v2.1.0` | Integrações |
| Sprint 6 | `v3.0.0` | **Jarvis Completo** |

---

## ⚡ O que MANTER do projeto atual

- ✅ `prompt_kuri.txt` — A personalidade é perfeita, não mude.
- ✅ Sistema emocional do `brain.py` — O emotional_context já é ótimo.
- ✅ Chaves de API (Grok, ElevenLabs) — Continuam sendo usadas.
- ✅ Widget PyQt6 com avatar animado — Base sólida premium atingida na Sprint 3.
- ✅ Function calling no brain.py — Padrão correto (bug de HTTP Client fixado).
- ✅ Cache de TTS — Implementação eficiente.

## ⚠️ O que foi REMOVIDO/SUBSTITUÍDO

- ❌ FastAPI — Não precisa de server HTTP. Kuri roda direto no desktop.
- ❌ HeyGen — Caro demais. Substituído pelo avatar visual local (MP4 loop).
- ❌ `httpx` como backbone — Mantido apenas para chamadas de API (com lifecycle fixado na v1.3).

---

## 🧭 Evolução Visual

```
v0.1 (Início)       v0.5 (HOJE)           v1.0 (Sprint 3)       v2.0 (Sprint 4-5)     v3.0 (Sprint 6)
Chatbot API     →    Desktop Voice    →    Visual Premium   →    Jarvis Autônomo   →   Jarvis Completo
- Texto input        - Voz input           - Widget 300x400      - Algorithm 7 fases    - Acesso remoto
- API response       - Voz output          - Gradientes/glow     - Skills modulares     - Ollama local
- Sem memória        - Memória JSON        - Rotinas             - Aprendizado          - Visão comp.
- Sem ações          - 8 ações desktop     - Modo compacto       - Proatividade         - Multi-avatar
- Sem avatar         - Avatar 5 emoções    - Tray icon           - Integrações          - Full HUD
```

---

> [!TIP]
> **Próximo passo recomendado:** Completar os itens restantes da Sprint 4 (profiling, skills dinâmicas, hooks) ou iniciar a **Sprint 5** (Integrações Externas: YouTube, Git, GitHub).

> [!WARNING]
> **APIs pagas:** ElevenLabs tem limite de créditos. O cache (`tts_cache/`) já está implementado — mantenha-o SEMPRE ativo.
