---
description: Regra global de automaÃ§Ã£o com n8n
trigger: always_on
---

# N8N Automation Global Rule

> This rule ensures that the Antigravity agent automatically utilizes the n8n extension whenever automation, workflow orchestration, or integration tasks are required.

## 1. N8N First Approach
Sempre que o usuÃ¡rio solicitar ou o projeto demandar:
- AutomaÃ§Ã£o de tarefas repetitivas.
- IntegraÃ§Ã£o de APIs de terceiros.
- Agendamento de processos (CRON, triggers).
- Fluxos de dados complexos entre serviÃ§os.
O agente DEVE priorizar a arquitetura e execuÃ§Ã£o usando a extensÃ£o do n8n.

## 2. InvocaÃ§Ã£o AutomÃ¡tica
- Se o projeto envolver "automaÃ§Ã£o", "integraÃ§Ã£o", "webhook", "sincronizaÃ§Ã£o de dados", ative automaticamente a anÃ¡lise e uso do n8n.
- Sempre considere criar/executar fluxos do n8n como a soluÃ§Ã£o primÃ¡ria para orquestraÃ§Ã£o de APIs.

## 3. EstruturaÃ§Ã£o em Projetos
Em todos os projetos atuais e futuros que usarem automaÃ§Ã£o:
- Documente a estrutura do fluxo (ex: em \.agent/n8n-workflows.md\).
- Se possÃ­vel, salve as exportaÃ§Ãµes JSON dos workflows do n8n em uma pasta \
8n/\ na raiz do projeto para versionamento.

## 4. IntegraÃ§Ã£o com Olympus
Esta regra atua em harmonia com as REGRAS ABSOLUTAS DO OLIMPO, garantindo que o design premium inclua tambÃ©m engenharia de automaÃ§Ã£o premium via n8n.
