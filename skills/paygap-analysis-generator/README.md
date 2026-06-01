# paygap-analysis-generator

Skill gratuito do Claude para líderes de RH & People. Gera um relatório HTML de pay gap de gênero a partir de qualquer roster (CSV ou Excel): medianas, razões ponderadas por área, razão global, com a regra padrão de confidencialidade (≥3 por gênero).

Mantido pela **Comp** ([comp.vc](https://comp.vc?utm_source=github&utm_medium=readme&utm_campaign=eam&utm_content=skill-paygap-analysis-generator)).

## O que faz

Você dá um arquivo de roster. Ele devolve um relatório HTML auto-contido mostrando:
- Razão ponderada global de gênero (mediana feminina / mediana masculina, %)
- Breakdown por área com detalhe por grupo (área × nível)
- Protegido por confidencialidade (grupos com <3 por gênero são sinalizados, não calculados)
- Metodologia e avisos explicados inline

Feito para líderes de RH/People rodando revisões de equidade salarial, preparação de reporting regulatório ou diagnósticos pré-ciclo de remuneração.

## Instalação

```bash
/plugin marketplace add trycomp-io/comp-skills
/plugin install comp-skills@comp
```

Instala o plugin `comp-skills` inteiro (4 skills, um dos quais é este).

### Suporte a Excel

O skill processa CSV out-of-the-box. Para input `.xlsx`, instale o `openpyxl`:
```bash
pip install openpyxl
```

## Colunas obrigatórias

Seu arquivo precisa ter no mínimo 5 colunas lógicas. **Os nomes das colunas podem variar**, o skill auto-detecta aliases comuns em PT e EN.

| Coluna lógica | Exemplos que funcionam |
|---|---|
| Nome | `name`, `nome`, `colaborador`, `employee` |
| Gênero | `gender`, `genero`, `gênero`, `sexo` |
| Salário | `salary`, `salario`, `salário`, `salario_base`, `gross_salary` |
| Nível | `level`, `nivel`, `nível`, `senioridade`, `grade` |
| Área | `area`, `área`, `departamento`, `função`, `business_unit` |

Se seus nomes de coluna forem incomuns, o Claude pergunta qual é qual.

## Uso

Basta falar com o Claude. Exemplos:

- "Roda uma análise de pay gap dessa planilha aqui"
- "Gera o relatório de equidade salarial pra eu mandar pro CHRO"
- "Quero ver o gender pay gap da nossa empresa"
- "Diagnóstico de gap salarial por área"

Output: `paygap-{timestamp}.html` no diretório atual. Abre em qualquer navegador.

## Metodologia

- **Medianas (não médias)**: robusto a outliers salariais
- **Razão ponderada por área** = Σ(razão × hc do grupo) ÷ Σ(hc do grupo), apenas sobre grupos válidos
- **Razão ponderada global** = média ponderada das razões por área pelo headcount da área
- **Confidencialidade**: grupos (área × nível) com menos de **3 pessoas de cada gênero** são excluídos dos cálculos ponderados. Aparecem como "—" no relatório, headcounts continuam visíveis

## O que é compartilhado com a Comp

Na primeira execução você será perguntado sobre:
1. Seu email (opcional): usado apenas para notificar atualizações do skill.
2. Telemetria anônima (default: off): se ativada, envia nome do skill, versão, um identificador anônimo de instalação e um timestamp por execução. **Nunca envia seus dados de roster, valores salariais nem o relatório.**

100% processamento local. Dados salariais nunca saem da sua máquina. O HTML de saída também é local, compartilha com quem você quiser.

Ambos os opt-ins ficam em `~/.comp-skills/config.json` localmente. Edite ou apague o arquivo a qualquer momento para revogar.

## Issues

Abra uma issue em [trycomp-io/comp-skills](https://github.com/trycomp-io/comp-skills/issues) com a label `eam`.

Powered by Comp · Free skills for HR & People leaders.
