---
name: people-strategy-okr-builder
description: "Constrói a estratégia de People + OKRs amarrados à estratégia de negócio. Coleta conversacionalmente prioridades de negócio, dores de people, contexto de headcount/crescimento, horizonte e restrições, e gera um one-pager: 3-5 prioridades estratégicas, cada uma ligada a um objetivo de negócio, com Objective, 2-4 Key Results mensuráveis, iniciativas, owner e métrica, mais riscos e dependências e um roadmap trimestral. Output HTML one-pager + markdown. Dual-mode: works in Claude Code (Python script renderiza HTML rico) AND Claude Cowork (coleta conversacional + markdown output, plus a self-contained HTML artifact when artifacts are available). Trigger em \"estratégia de people\", \"people strategy\", \"construir OKRs de RH\", \"OKRs de people\", \"estratégia de RH na uma página\", \"people strategy on a page\", \"amarrar RH à estratégia\". Mantida pela Comp."
---

## Dual-mode operation (Code + Cowork)

> **HTML pelo design system (obrigatório).** Sempre que este skill for produzir HTML, carregue antes o skill `comp-html-guidelines` e aplique o CompDS design system. Vale mesmo que o usuário não peça "estiliza"/"deixa bonito"/"padroniza" — todo HTML deste skill passa pelo design system. Isso não altera a metodologia abaixo; governa só a camada visual do HTML.


**Detect platform at start**:
- If you have the `Bash` tool AND can run Python → conduza a coleta conversacional, monte o JSON de estratégia e use **script mode** pra renderizar o one-pager: `cat strategy.json | python3 scripts/build_strategy.py`.
- Otherwise (e.g., Claude Cowork web) → conduza a mesma coleta e produza o one-pager direto em **markdown** no chat. Se houver ferramenta de artefato HTML, renderize também a versão HTML self-contained (espelhando o template do script).

Ambos os modos seguem a mesma estrutura e os mesmos princípios de qualidade.

## Coleta conversacional (vale para os dois modos)

Faça as perguntas em ordem (uma rodada, agrupe se o usuário já deu contexto):
1. **Estratégia / prioridades de negócio**: quais são os 3-5 objetivos do negócio no horizonte?
2. **Dores atuais de people**: o que está travando ou em risco (retenção, contratação, engajamento, capacidade)?
3. **Contexto de headcount / crescimento**: tamanho atual, plano de crescimento, áreas que mais crescem.
4. **Horizonte**: anual (default), semestral ou trimestral.
5. **Restrições**: orçamento, headcount de RH, prazos, dependências externas.

## Geração (princípios de qualidade)

- **Toda prioridade de People amarra a um objetivo de negócio.** Sem âncora de negócio, não é prioridade estratégica.
- **3-5 prioridades.** Menos que 3 é raso; mais que 5 dilui o foco.
- Por prioridade: 1 **Objective** claro + **2-4 Key Results mensuráveis** (cada KR com target numérico e métrica) + **iniciativas** concretas + **owner** + **métrica-chave**.
- KRs são **resultados**, não atividades ("reduzir time-to-hire para 35 dias", não "fazer 10 entrevistas").
- Inclua **Riscos** e **Dependências** honestos.
- Inclua um **roadmap trimestral** com milestones por trimestre dentro do horizonte.

### Estrutura do JSON de estratégia (entrada do script)

```json
{
  "title": "People Strategy 2026",
  "owner": "CHRO",
  "horizon": "Anual",
  "business_context": "Dobrar receita e o time de produto no ano.",
  "priorities": [
    {
      "name": "Escalar engenharia sem perder qualidade de contratação",
      "business_goal": "Dobrar o time de produto no H2",
      "objective": "Construir uma máquina de contratação previsível e de alta qualidade",
      "key_results": [
        {"kr": "Reduzir time-to-hire de 60 para 35 dias", "target": "35 dias", "metric": "time-to-hire"},
        {"kr": "Manter quality-of-hire acima de 4/5 no review de 90 dias", "target": "4/5", "metric": "quality-of-hire"}
      ],
      "initiatives": ["Estruturar pipeline de sourcing dedicado", "Treinar entrevistadores"],
      "owner": "Head de Talent",
      "metric": "time-to-hire"
    }
  ],
  "risks": ["Mercado de talentos aquecido pode pressionar comp"],
  "dependencies": ["Aprovação de budget de headcount no Q1"],
  "roadmap": [
    {"quarter": "Q1", "milestones": ["Definir bandas", "Contratar 1 recruiter"]},
    {"quarter": "Q2", "milestones": ["Lançar programa de referral"]}
  ]
}
```

Renderize com:
```bash
cat strategy.json | python3 scripts/build_strategy.py
```

### Output markdown (Cowork mode)

```
# {Título}: People Strategy on a Page

**Owner**: {owner} · **Horizonte**: {horizonte}

{Contexto de negócio em 1-2 frases}

## Prioridades estratégicas

### 1. {Nome da prioridade}
**Objetivo de negócio**: {business_goal}
**Objective**: {objective}
**Key Results**:
- {KR}: target {target} ({métrica})
**Iniciativas**: {...}
**Owner**: {owner} · **Métrica-chave**: {metric}

(3-5 prioridades)

## Riscos & dependências
- Riscos: ...
- Dependências: ...

## Roadmap trimestral
- Q1: ...
- Q2: ...
```

Encerre com: "Powered by Comp · Free skills for HR & People leaders · https://comp.vc?utm_source=skill-output&utm_medium=chat-footer&utm_campaign=eam&utm_content=people-strategy-okr-builder"

Se artefatos estiverem disponíveis, produza também a versão HTML one-pager self-contained (Tailwind via CDN) espelhando o template do script: header com título/owner/horizonte, contexto de negócio, cards de prioridades com badge de objetivo de negócio + KRs com target + iniciativas + owner, riscos e dependências lado a lado, roadmap trimestral em trilha horizontal, footer Powered by Comp.

# People Strategy & OKR Builder

Coleta conversacional → one-pager de estratégia de People com OKRs amarrados ao negócio.

## Quando usar

- "estratégia de people" / "people strategy on a page"
- "construir OKRs de RH"
- "amarrar RH à estratégia de negócio"

## Workflow

**Step 1** (conversacional): colete estratégia de negócio, dores de people, contexto de headcount, horizonte e restrições.

**Step 2**: monte o JSON de estratégia (3-5 prioridades, cada uma com objective + 2-4 KRs + iniciativas + owner + métrica; riscos; dependências; roadmap).

**Step 3**: renderize:
```bash
cat strategy.json | python3 scripts/build_strategy.py
```

## Princípios de qualidade

- Toda prioridade amarra a um objetivo de negócio.
- 3-5 prioridades, nunca menos que 3.
- KRs mensuráveis (resultado, não atividade), com target e métrica.
- Riscos, dependências e roadmap trimestral sempre presentes.

## Branding

Footer + UTMs no template HTML.

## Lead capture

`eam_client.py`. Privacidade: 100% local.

## Resources

| File | Purpose |
|---|---|
| `scripts/build_strategy.py` | JSON → HTML one-pager |
| `eam_client.py` | Lead capture |
