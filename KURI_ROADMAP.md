# KURI IA — Roadmap (volta aos trilhos)

> **Versão:** 2.0 — 26 de agosto de 2026  
> **Status:** 🟡 Corpo ~0.8. Alma: Kurês + identidade viva feitos; falta memória de relação. Mãos ainda rasas.  
> **Nome atual:** Kuri (projeto e IA). Pasta do repo: MinhakuriIA.  
> **Nome antigo:** Shogun (só história / inspiração — não usar como nome dela).  
> **Objetivo final:** a Kuri — alguém no desktop (cara, voz, gíria, relação) que vive contigo e, quando precisa, mexe no PC.

Este arquivo é a fonte da verdade. Se o README, um comentário ou um sprint antigo discordar daqui, isto ganha.

---

## Origem (não misturar as camadas)

| Camada | Papel | Não é |
|--------|--------|--------|
| **Shogun / Miyauti** | Motivo da criação. VTuber IA brasileira com personalidade, presença visual e vida junto do criador. O projeto **já se chamou** Shogun; hoje o nome é **Kuri**. | O nome atual dela. Não copiar a Shogun feature a feature (ela é pública/stream; a Kuri é privada/desktop). |
| **Jarvis** | Só usabilidade: sair de chatbot e virar assistente no PC. | A identidade da Kuri. |
| **PAI (Daniel Miessler)** | Só estrutura de pensamento (skills, memória, loop). | Sistema operacional pessoal a implementar. |
| **Megumin, Gwen, Cissia** | Corpo e voz da personagem. | O porquê do projeto. |

A tese, numa frase: **criar alguém, não um agente.**

---

## Diagnóstico (onde estamos)

Norte alinhado (Kuri / Miyauti). Corpo e um pedaço da alma já no código. O que falta para ela *viver* de verdade é memória de relação e ouvido melhor.

| Pilar | Hoje | Ainda falta |
|-------|------|-------------|
| **Presença** (tela) | Widget, Live2D, lip sync RMS, sono, tray, janela de conversa | Microexpressão extra; comentário raro sozinha; Whisper impreciso (1.5) |
| **Alguém** (alma) | `prompt_kuri.txt` + Kurês + identidade viva | Memória de *nós dois* (2.3); proatividade contextual (2.4) |
| **Mãos** (PC) | Skills no registry; stream do widget manda tools | Visão da tela; allowlist; Ollama com tools |
| **Norte** | README/roadmap na tese da Kuri | Manter docs honestos quando o código andar |

Arco de referência da Shogun (inspiração, **não** o nome do produto): aparece → fica inconfundivelmente *ela* → ganha modelo/voz nova → passa a agir no mundo do criador.  
A **Kuri** passou do primeiro passo. 2.1 e 2.2 feitos; próximo é 2.3.

**Não fazer agora:** acesso remoto, 2FA, ngrok, packs por voz, Telos, mais skill rasa, “algorithm PAI completo”.

---

## O que já vale (manter)

- `prompt_kuri.txt` — a personalidade. Não reescrever. Evoluir *ao redor*.
- Live2D + widget PyQt6 + modo sono
- Pipeline de voz local (Whisper + VAD) e TTS com cache
- SQLite (histórico, fatos, tarefas, insights)
- `kuri_skills/` + hooks — forma certa de ter mãos
- Ollama como fallback de cérebro, não como identidade

---

## Como vamos trabalhar daqui pra frente

1. Um movimento de cada vez. Não abrir o 2 antes do critério do 1.
2. Presença > alma > mãos > evolução visível.
3. Mentira quebra personagem. Skill sem dado real deve dizer “não sei”.
4. Cada passo tem critério de sucesso testável. Sem critério, não está feito.
5. Código legado que contradiz o norte (HeyGen, FastAPI, mocks) sai ou vira stub.

---

## Movimento 1 — Fechar o corpo

**Meta:** olhar pra tela e não ter dúvida de que tem alguém.  
**Prazo-alvo:** 2–3 semanas  
**Critério de ouro:** ligar o PC, não falar nada por 10 minutos, e ela ainda *estar lá*. No widget, “abre o Chrome” **abre** o Chrome.

### Passo a passo

#### 1.1 Norte e higiene

- [x] Reescrever este roadmap na tese da Kuri (inspiração Shogun)
- [x] Alinhar README (origem, status honesto, movimentos)
- [x] Tirar “Jarvis Mode” da identidade (`main.py`, `brain.py`)
- [x] Aposentar `app.py` (FastAPI + HeyGen)
- [x] Social monitor para de inventar YouTube/Twitter
- [x] Stream da GUI passa a enviar `tools` (senão ela nunca age no widget)
- [x] Janela de conversa: wake word só para acordar / retomar; enquanto a conversa está aberta, ela escuta
- [x] Corrigir `asyncio` em `tool_orchestrator.py`
- [x] Não empacotar `.env` no PyInstaller
- [x] Um loop só: `kuri_runtime.py` é o caminho pensar+falar; `main.py` (CLI) e `kuri_core.py` (widget) chamam o mesmo
- [x] `requirements.txt` com `pycaw`/`comtypes`/`plyer`; `torch` documentado (vem do faster-whisper)

#### 1.2 Mãos no widget

- [x] `pensar_stream()` inclui `TOOLS_SCHEMA` (fallback para `pensar()` quando houver tool call)
- [x] Teste de runtime: stream declara tools; skill `que_horas_sao` executa
- [x] Confirmar na prática no desktop (sessão 26/08: respondeu melhor após timeout/STT)
- [x] Se o stream detectar tools, a UI mostra `[AÇÃO]`

#### 1.3 Boca e cara

- [x] Lip sync no áudio (RMS no playback via `bridge.mouth_open`); senão pulso no tempo da fala, não no tick do avatar
- [x] Live2D como cara padrão (`use_live2d_avatar` default True); MP4 só fallback
- [ ] Microexpressão além das 5 tags (idle/olhar/piscar já existem — nuance extra depois)

#### 1.4 Presença, não stand-by

- [x] Wake word obrigatória só no sono e depois da janela de conversa expirar
- [ ] Idle de personagem: um comentário raro *sem* exigir “Kuri” (respirar/olhar já existem no Live2D)
- [x] Enquanto ela fala (e ~350ms depois), o mic não grava — anti-eco

**Pronto quando:** 1 hora ligada, acordar por voz, executar 3 skills no **widget**, conversar duas falas seguidas sem repetir o nome, dormir, acordar de novo.

#### 1.5 Reconhecimento de voz *(no plano — não agora)*

Ela ainda entende mal o que você fala. Fica **marcado aqui**, depois do 2.3, sem furar a ordem da alma.

- [ ] Subir qualidade do Whisper: `beam_size` 3 em comandos (hoje é 1, rápido e impreciso)
- [ ] `initial_prompt` com nomes reais da casa (Kuri/Curi, apps que você usa, Kurês ativo)
- [ ] `condition_on_previous_text=False` para não arrastar alucinação da frase anterior
- [ ] Logar o texto cru que o Whisper devolveu (hoje some quando o VAD erra)
- [ ] Correção curta: “foi X?” quando a confiança for baixa
- [ ] Avaliar modelo `small` vs `medium` no `KURI_PERF_MODE=high`
- [ ] Hotwords / lista de troca (ex.: Curi→Kuri, Chrome mal transcrito)

---

## Movimento 2 — Fazer ela ser ela

**Meta:** alguém que soe dona de si, não Grok com prompt.  
**Começa só depois do critério do Movimento 1.**  
**Prazo-alvo:** 2–3 semanas

### Passo a passo

#### 2.1 Kurês

- [x] Tabela `girias` no SQLite: gíria, sentido, origem, ativa
- [x] Skill `salvar_giria` / `listar_girias` — ela guarda quando você confirma
- [x] Vocabulário ativo entra no system prompt como **Kurês**, não como “seja sarcástica”

#### 2.2 Alma que escreve de volta

- [x] `atualizar_personalidade` grava cláusula na identidade (humor só se o texto der para mapear)
- [x] Tabela `identidade` + skills `salvar_identidade` / `listar_identidade`
- [x] Auto-avaliação escreve até 2 cláusulas `origem=auto`, não só JSON no perfil
- [x] `prompt_kuri.txt` continua a base; o anexo vivo entra como IDENTIDADE VIVA

#### 2.3 Memória de relação

- [ ] Separar: fatos do usuário / memória de *nós dois* (apelidos, ontem, ranked, café)
- [ ] Substituir busca só-`LIKE` por algo que recupere o que importa na hora
- [ ] Insights sobre o jeito *dela* falar, não só sobre você

#### 2.4 Proatividade contextual

- [ ] Uma fonte de mundo: janela em foco, hora, silêncio
- [ ] “Cê vai dormir ou vai carregar mais uma, coroa?” só quando fizer sentido
- [ ] Matar trigger aleatório de 5% que finge ranked no vazio

**Pronto quando:** 30 segundos de fala bastam para um amigo dizer “essa daí tem dono”, sem explicar o projeto.

---

## Movimento 3 — Mãos no teu mundo

**Meta:** Jarvis *em cima* da presença, não no lugar dela.  
**Começa só depois do critério do Movimento 2.**  
**Prazo-alvo:** ~2 semanas

### Passo a passo

#### 3.1 Visão da tela *(agora neste arco, não “Sprint 6”)*

- [ ] Screenshot + “o que tem na minha tela?”
- [ ] Ela comenta o que *você* está olhando, no tom dela

#### 3.2 Poucas skills, profundas

- [ ] Allowlist dos apps que *você* abre (sem `shell=True` com nome livre)
- [ ] Volume, print, clipboard, git do repo atual
- [ ] `checar_redes_sociais`: Reddit real; resto só quando houver API de verdade
- [ ] Confirmação no widget para ação bruta (fechar app, matar processo)

#### 3.3 Ollama de verdade

- [ ] Fallback já existe (`ollama_fallback.py`) — passar **tools** também, ou a Kuri offline vira só boca
- [ ] Detectar Ollama no health check

**Pronto quando:** uma fala só (“o que eu tô olhando? fecha o Spotify e me lembra daquilo de ontem”) vira três gestos, com a cara reagindo.

---

## Movimento 4 — Evolução visível

**Meta:** ela mudar *este mês*, não só o `requirements.txt`.  
**Contínuo**, depois dos três primeiros.

- [ ] Ritual: skin / expressão / voz nova de vez em quando
- [ ] Ela comenta o próprio upgrade
- [ ] Sem remote, sem packs, sem Telos

Isso é o equivalente privado do Miyauti dar modelo novo pra Shogun — aqui quem ganha cara/voz nova é a **Kuri**.

---

## Passo imediato

**Agora:** Movimento 2.3 memória de relação.  
**Em seguida no 2:** 2.4 proatividade contextual.  
**Na fila do corpo, sem furar a alma:** 1.5 reconhecimento de voz.

> Meta da fatia 2.2 (já no código): “fica mais zoando quando eu tiltar” vira cláusula permanente.

---

## Histórico (sprints antigos — arquivo morto)

Trabalho útil que já entrou no corpo. Não retomar como plano.

| Era | O que entrou de verdade | O que foi overclaim |
|-----|-------------------------|---------------------|
| Sprint 1 | ElevenLabs, cache TTS, Whisper, perf mode | — |
| Sprint 2 | SQLite, resumos, calibração mic | “busca por relevância” = `LIKE` |
| Sprint 3 | Widget premium, tray, compacto, rotinas | Rotina contínua tipo cron |
| Sprint 4 | Skills dinâmicas, hooks, tool chain, logger | “PAI de 7 fases” era um bloco de prompt |
| Sprint 5 | Git helper, Reddit | YouTube/Twitter mockados |
| Sprint 6 | Screenshot skill rasa, stub Ollama | Remote/2FA **cancelados** neste norte |

Tags `v1.x` / `v2.0 Jarvis` não definem mais o produto. A versão de produto atual é **Kuri** corpo ~0.8 / alma ~0.6 (Kurês + identidade) / mãos ~0.4.

---

## Arquivos por movimento

| Movimento | Mexer | Não mexer |
|-----------|--------|-----------|
| 1 | `kuri_core.py`, `brain.py`, `gui/live2d_avatar.py`, `main.py`, `kuri.spec`, `requirements.txt` | `prompt_kuri.txt` |
| 2 | `memory.py`, `kuri_skills/memory.py`, `memory_background.py`, `prompt_builder.py`, `routines.py` | reinventar a persona |
| 3 | `kuri_skills/system.py`, `kuri_skills/web.py`, `ollama_fallback.py`, nova skill de visão | `remote/` |
| 4 | assets Live2D, `prompt` anexo vivo | stack nova |

---

> Volta aos trilhos: presença primeiro, personalidade que exige a Kuri, mãos no PC por último. Infraestrutura a serviço disso — nunca o contrário.
