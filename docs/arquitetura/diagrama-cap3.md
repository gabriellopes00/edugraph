# Diagrama de componentes — figura de abertura do capítulo 3

A leitura é uma só: **as três frentes só se tocam através da coluna
central**, que é o layout de artefatos em disco (ADR-0001). Os rótulos
históricos ficam fora do grafo e entram apenas pela linha tracejada da
validação (ADR-0008).

Para o artigo, exportar em SVG:

```bash
# com a extensão Mermaid do VS Code, ou:
npx -y @mermaid-js/mermaid-cli -i docs/arquitetura/diagrama-cap3.md -o results/figures/fig1-arquitetura.svg
```

```mermaid
flowchart LR
  subgraph SRC["Fontes"]
    OULAD[("OULAD · 7 CSV")]
    SYN[("Gerador sintético · seed fixa")]
  end

  subgraph FA["Frente A · Dados e Modelagem"]
    ETL["ETL → tabela normalizada"]
    BIP["Grafo bipartido G = (U ∪ V, E)"]
    PROJ["Projeções: simples · alocação de recursos"]
  end

  subgraph DISK["Contratos em disco · data/fixtures ou data/processed"]
    D1[["bipartite/"]]
    D2[["projections/"]]
    D3[["communities/"]]
    D4[["centrality/"]]
    D5[["metrics/"]]
    D6[["outcomes.csv · rótulos fora do grafo"]]
  end

  subgraph FB["Frente B · Comunidades"]
    LOU["Louvain"]
    GN["Girvan-Newman + orçamento de tempo"]
    Q["Q à mão × NetworkX"]
    CHAR["Caracterização por disciplina"]
  end

  subgraph FC["Frente C · Centralidade e Aplicação"]
    CEN["Grau · Intermediação · Autovetor"]
    CRIT["Disciplinas críticas"]
    API["FastAPI somente leitura"]
    UI["React + Vite · Cytoscape.js"]
  end

  VAL["Validação a posteriori"]

  OULAD --> ETL
  SYN --> ETL
  ETL --> BIP --> PROJ
  BIP --> D1
  PROJ --> D2
  D2 --> LOU --> D3
  D2 --> GN --> D3
  D3 --> Q
  D1 --> CHAR
  D3 --> CHAR
  D2 --> CEN --> D4
  D4 --> CRIT
  D2 --> API
  D3 --> API
  D4 --> API
  API --> UI
  D3 --> D5
  D4 --> D5
  D6 -.-> VAL
  D3 -.-> VAL
  D4 -.-> VAL
```

## O que cada frente produz e consome

**`[A]` Dados e Modelagem** produz `bipartite/`, `projections/`, `outcomes.csv` e
`metrics/projections.csv`. Consome só CSV bruto.

**`[B]` Comunidades** produz `communities/` (partição, perfil, Q, tempo,
status) e `metrics/communities.csv`. Consome `projections/` e
`bipartite/`; lê `outcomes.csv` apenas na validação.

**`[C]` Centralidade e Aplicação** produz `centrality/`, `metrics/centrality_top.csv`, a API
e a interface. Consome `projections/`, `communities/` e os próprios
`centrality/`.

## Legenda para o texto do artigo

- **Caixas cilíndricas** (`Fontes`): dados brutos, fora do controle do
  sistema.
- **Caixas duplas** (`Contratos em disco`): artefatos versionados por
  esquema, cada um com o `meta.json` que registra a especificação que o
  gerou.
- **Setas cheias**: fluxo de dados do pipeline.
- **Setas tracejadas**: validação a posteriori — o único caminho por onde
  um rótulo histórico entra, e ele **termina** na validação, nunca
  realimenta o pipeline.

Esse último ponto é o que o diagrama comunica melhor do que um parágrafo:
não há seta saindo de `outcomes.csv` para nenhum algoritmo.
