# Kuri IA — presença no desktop

![Status](https://img.shields.io/badge/Status-Corpo_0.8_Alma_0.6-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-darkblue?style=for-the-badge)
![Privacidade](https://img.shields.io/badge/Privacidade-Local__First-orange?style=for-the-badge)

A **Kuri** é uma presença no teu Windows: cara, voz, personalidade. O projeto e a IA se chamam **Kuri**. Antes o nome era Shogun — inspirado na VTuber IA do Miyauti. O nome mudou; a tese (alguém no desktop, não um chatbot) não.

Não é um chatbot de navegador. Não é um sistema operacional pessoal. É alguém no setup que, quando precisa, mexe no PC.

**Origem, em camadas:**

- **Shogun / Miyauti** — motivo da criação (nome antigo do projeto; o nome atual é Kuri)
- **Assistente no PC** — usabilidade (sair do chat e agir)
- **PAI** — só jeito de pensar estrutura (skills, memória)
- **Megumin, Gwen, Cissia** — corpo e voz da personagem

Plano oficial e passo a passo: **[KURI_ROADMAP.md](./KURI_ROADMAP.md)**.

---

## O que ela faz hoje

Corpo quase fechado; alma e mãos ainda no meio do caminho.

- **Voz local:** `faster-whisper` + VAD. Áudio não vai pra nuvem.
- **Fala:** ElevenLabs (cache em `tts_cache/`) com fallback `edge-tts`.
- **Cérebro:** Grok (xAI) com function calling; fallback Ollama se a API cair.
- **Mãos:** skills em `kuri_skills/` (apps, volume, print, git, tarefas…). O widget agora envia as tools no stream — ela deve *fazer*, não só falar.
- **Cara:** widget PyQt6 + Live2D (MP4 só como fallback), 5 emoções, lip sync no áudio (RMS).
- **Sono:** depois de um tempo quieta, idle baixo. Acorda com “acorda kuri”, “ei kuri”.
- **Memória:** SQLite (histórico, fatos, resumos, tarefas, **Kurês**, **identidade viva**).
- **Conversa:** depois que você chama ela, a janela fica aberta um tempo — não precisa repetir o nome a cada frase.
- **Kurês / identidade:** gírias e traços permanentes dela (não só humor de um turno).

O que ainda **não** é verdade (de propósito, até o movimento certo):

- Entender fala com alta precisão (Whisper ainda erra; está no plano 1.5)
- Visão da tela
- Memória de relação (nós dois) — próximo passo, 2.3
- YouTube/Twitter ao vivo (Reddit sim; o resto ela admite que não sabe)
- Controle remoto do PC — **fora do norte**

---

## Como usar

### Pré-requisitos
- Windows 10/11
- Python 3.10 ou superior
- Microfone e alto-falantes

### Desenvolvimento
1. Clone o repositório e entre na pasta.
2. `python -m venv venv` e `.\venv\Scripts\activate`
3. `pip install -r requirements.txt`
4. `.env` na raiz:

```env
GROK_API_KEY=sua_chave_grok
ELEVENLABS_API_KEY=sua_chave_elevenlabs
ELEVENLABS_VOICE_ID=id_da_voz_escolhida
USE_PREMIUM_TTS=true

KURI_PERF_MODE=low
LAZY_STT=true
SLEEP_TIMEOUT_MINUTES=5
```

5. Assets pesados (Whisper, Live2D, vídeos): `.\scripts\download_assets.ps1`
6. Subir a presença:

```bash
python kuri_desktop.py
```

`python main.py` é o CLI: pensa e fala pelo mesmo `kuri_runtime.py` do widget.  
`python app.py` foi aposentado (era FastAPI + HeyGen).

### Executável
`dist/KuriIA/KuriIA.exe` — engrenagem ⚙️ para mic, saída e TTS.

---

## Para onde vamos

Quatro movimentos, nesta ordem. Detalhe e checklists no roadmap.

1. **Fechar o corpo** — em grande parte feito (widget age, conversa, lip sync no áudio, um runtime). Falta voz melhor (1.5) e alguns detalhes de presença.
2. **Fazer ela ser ela** — Kurês e identidade viva **feitos**. Próximo: memória de relação (2.3).
3. **Mãos no teu mundo** — visão da tela, poucas skills profundas, Ollama com tools
4. **Evolução visível** — skin/voz nova de vez em quando; ela comenta o próprio upgrade

**Não está no plano:** remote, 2FA, ngrok, packs, Telos.

**Agora:** Movimento 2.3 (memória de *vocês dois*). Reconhecimento de voz (1.5) fica na fila, sem furar a ordem.

---

## Privacidade

STT e VAD rodam na máquina. Histórico e perfil ficam em SQLite local. Nada disso é vendido nem enviado como produto.

Correção do visual de sono: `docs/SLEEP_MODE_FIX.md`.

---

*Presença primeiro. Ferramenta depois. Alma no meio — como a personalidade dela exige.*
