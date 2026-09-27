# 📜 Kuri IA — Lista Completa de Skills (Ferramentas)

**Total de Skills:** 28  
**Data da geração:** 2026-08-26  
**Como usar:** A Kuri ativa essas skills automaticamente quando você pede algo que combina com a descrição. Você também pode pedir explicitamente ("Kuri, use a skill diagnosticar_sistema").

As skills são carregadas dinamicamente da pasta `kuri_skills/`. Você pode recarregar com a skill `recarregar_skills`.

---

## 🔧 Skills do Sistema (Controle do PC)

### abrir_aplicativo
**Descrição:** Abre um aplicativo no computador do usuário.

**Parâmetros:**
- `nome` (string, obrigatório): Nome do aplicativo (ex: `chrome`, `notepad`, `calculadora`, `cmd`...)

**Exemplos:**
- "Abre o Chrome"
- "Abra o bloco de notas"

---

### fechar_aplicativo
**Descrição:** Fecha um aplicativo que está rodando.

**Parâmetros:**
- `nome` (string, obrigatório)

**Exemplos:**
- "Fecha o Spotify"
- "Feche o Chrome"

---

### ajustar_volume
**Descrição:** Controla o volume do sistema.

**Parâmetros:**
- `acao` (string, obrigatório): `aumentar`, `diminuir`, `mutar`, `desmutar`

---

### capturar_tela
**Descrição:** Tira um screenshot e salva na Área de Trabalho.

**Sem parâmetros.**

---

### enviar_notificacao
**Descrição:** Envia uma notificação toast no Windows.

**Parâmetros:**
- `titulo` (string)
- `mensagem` (string)

---

### informacao_sistema
**Descrição:** Retorna CPU, RAM, disco, bateria e SO.

---

### listar_processos
**Descrição:** Lista os processos com maior uso de CPU e RAM.

---

### ler_clipboard
**Descrição:** Lê o conteúdo atual da área de transferência.

---

### que_horas_sao
**Descrição:** Diz a hora e data atual.

---

## 📁 Gerenciamento de Arquivos e Pastas

### criar_pasta
**Descrição:** Cria uma nova pasta na Área de Trabalho.

**Parâmetro:** `nome`

### abrir_pasta
**Descrição:** Abre pastas conhecidas (downloads, documentos, desktop, imagens, musicas, videos) ou caminho absoluto.

---

## 🧠 Memória e Personalidade

### salvar_fato_usuario
**Descrição:** Salva um fato importante sobre você para memória de longo prazo.

**Parâmetro:** `fato`

**Exemplo:** "Salva que eu gosto de café amargo"

### atualizar_perfil_usuario
**Descrição:** Atualiza nome, apelidos ou humor atual.

**Parâmetros:**
- `campo`: `nome_usuario`, `apelidos`, `humor_atual`
- `valor`

### salvar_giria
**Descrição:** Guarda uma gíria/bordão no Kurês.

**Parâmetros:** `giria` (obrigatório), `sentido` (opcional)

### listar_girias
**Descrição:** Lista o Kurês ativo.

### atualizar_personalidade
**Descrição:** Ajusta humor (se der) E grava traço na identidade viva. Não é só um enum.

**Parâmetro:** `instrucao` (ex: "fica mais sarcástica", "zoar mais quando eu tiltar")

### salvar_identidade
**Descrição:** Grava um traço permanente (ex: "zoar mais quando ele tiltar no LoL").

### listar_identidade
**Descrição:** Lista os traços ativos da identidade viva.

---

## ✅ Tarefas (To-Do)

### gerenciar_tarefa
**Descrição:** Cria, conclui ou remove tarefas.

**Parâmetros:**
- `acao`: `criar`, `concluir`, `remover`
- `titulo` (para criar)
- `task_id` (para concluir/remover)
- `prioridade` (opcional, 1-3)

### listar_minhas_tarefas
**Descrição:** Lista todas as tarefas pendentes.

---

## 🛠️ Desenvolvimento e Projetos

### git_status
**Descrição:** Status do repositório Git atual (branch + alterações).

**Parâmetro opcional:** `repo_path`

### listar_projetos_desenvolvimento
**Descrição:** Encontra repositórios Git em uma pasta base.

### resumo_projeto
**Descrição:** Lê e resume README.md ou ROADMAP.md de um projeto.

**Parâmetro:** `projeto_path`

### sugerir_proximos_passos
**Descrição:** Analisa Git + Roadmap e sugere próximos passos.

---

## 🌐 Web e Redes Sociais

### pesquisar_web
**Descrição:** Faz busca no Google e abre no navegador.

**Parâmetro:** `query`

### checar_redes_sociais
**Descrição:** Consulta posts reais do Reddit. YouTube/X ainda não têm API — ela admite que não sabe, não inventa trend.

---

## 🩺 Diagnóstico e Manutenção

### diagnosticar_sistema
**Descrição:** Diagnóstico completo: skills carregadas, saúde, humor atual, modelo Whisper, dependências, etc.

**Sem parâmetros.** (Muito útil para debug)

### recarregar_skills
**Descrição:** Recarrega todas as skills dinamicamente sem reiniciar a Kuri.

---

## Dicas de Uso

- Peça normalmente: "Kuri, que horas são?" ou "Kuri, lista minhas tarefas"
- Peça explicitamente: "Kuri, use diagnosticar_sistema"
- Algumas skills têm dependências declaradas (Fase 3) — o sistema avisa se algo estiver faltando.
- Você pode pedir para a Kuri "atualizar personalidade" ou "salvar fato".

---

**Quer que eu adicione exemplos de uso mais detalhados, diagramas ou uma versão em tabela para referência rápida?**

---

## 😴 Modo Sono (Sleep Mode) — Feature do Sistema

A Kuri possui um **modo sono / suspenso** para reduzir drasticamente o consumo de CPU quando fica rodando em background por longos períodos.

### Como funciona
- **Entrada automática**: Após `SLEEP_TIMEOUT_MINUTES` (padrão 5) de inatividade, a Kuri entra em modo sono.
- **Comportamento em sono**:
  - Ignora comandos normais (não processa LLM nem responde).
  - Avatar vai para estado visual relaxado (usa "idle" do Live2D + deep idle a ~1 FPS).
  - Reduz tarefas em background.
- **Acordar**:
  - Diga frases como: **"acorda kuri"**, **"kuri acorda"**, **"acorda"**, **"ei kuri"**, **"acorde"**.
  - A Kuri acorda imediatamente, carrega o modelo de voz se necessário e responde.
- **Configuração** (no `.env`):
  ```env
  SLEEP_TIMEOUT_MINUTES=5
  LAZY_STT=true
  KURI_PERF_MODE=low
  ```

Útil para deixar a Kuri sempre ligada sem gastar recursos desnecessários.

---

*Lista alinhada ao sistema atual (28 skills + comportamentos do sistema).*