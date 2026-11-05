# Documentação

O critério desta pasta é o da seção 11 do briefing: **se alguém do grupo
precisar responder "por que fizemos assim?" três semanas depois, ou na
banca, a resposta está aqui.** Nada de decisão importante morando só no
histórico do chat ou na cabeça de quem implementou.

## Por onde começar

| Se você quer… | Leia |
|---|---|
| entender um termo que apareceu (grafo, projeção, modularidade) | [glossario.md](glossario.md) |
| entender a arquitetura em 10 minutos | [arquitetura/visao-geral.md](arquitetura/visao-geral.md) |
| ver as pendências abertas | [../observacoes/](../observacoes/README.md) → o arquivo da frente e o `para-todos.md` |
| começar a trabalhar numa frente | [specs/README.md](specs/README.md) → o README da frente |
| saber por que algo foi decidido assim | [adr/README.md](adr/README.md) |
| implementar contra um contrato | [contratos/README.md](contratos/README.md) |
| entender por que ninguém espera por ninguém | [arquitetura/paralelismo.md](arquitetura/paralelismo.md) |
| escrever ou rodar testes | [testes/estrategia.md](testes/estrategia.md) |
| saber o que precisa entrar no texto do artigo | [artigo/decisoes-metodologicas.md](artigo/decisoes-metodologicas.md) |
| falar com o orientador sem enrolar | [orientador/README.md](orientador/README.md) |

## O que há aqui

### [`glossario.md`](glossario.md) — os termos, sem jargão

Grafo, bipartido, projeção, granularidade, modularidade, modelo nulo,
centralidade — cada um com desenho. É o primeiro lugar a mandar quem
chegou agora, ou quem travou numa palavra lendo uma spec.

### [`adr/`](adr/README.md) — decisões de arquitetura

Catorze ADRs no formato MADR curto. Só decisões que divergem ou detalham as
seções 2, 4 e 7 do briefing ganham ADR; divergir do starter kit não
precisa.

### [`contratos/`](contratos/README.md) — o que atravessa a fronteira

Um documento por contrato, espelhando `src/edugraph/contracts/`. O
pacote está **congelado**: mudança exige ADR e aprovação dos três.

### [`arquitetura/`](arquitetura/visao-geral.md)

- [visao-geral.md](arquitetura/visao-geral.md) — as seis decisões e o
  mapa do repositório
- [diagrama-cap3.md](arquitetura/diagrama-cap3.md) — a figura que abre o
  capítulo 3, em Mermaid
- [paralelismo.md](arquitetura/paralelismo.md) — as dependências reais e
  o que as neutraliza; a segunda-feira de cada frente
- [branches-e-merge.md](arquitetura/branches-e-merge.md) — o fluxo de
  trabalho

### [`specs/`](specs/README.md) — 21 specs, prontas para virar issue

Agrupadas por frente. Cada uma é executável em uma sessão de trabalho e
declara qual fixture substitui a dependência de outra frente.

### [`testes/`](testes/estrategia.md) — a estratégia que sustenta o paralelismo

Incluindo a derivação, no papel, dos valores esperados de `tiny_v1`.

### [`artigo/`](artigo/decisoes-metodologicas.md) — o que alimenta o texto

- [decisoes-metodologicas.md](artigo/decisoes-metodologicas.md) — o que
  precisa estar escrito, e o que o artigo **não** deve afirmar
- [indice-tabelas.md](artigo/indice-tabelas.md) — arquivo **gerado**. As
  figuras não são versionadas (decisão de 31/10/2026): `python -m edugraph
  figures --index` as lista, e os comandos de cada frente as geram sob demanda

### [`orientador/`](orientador/README.md) — o que se manda para a orientação

Uma **nota** avisa de decisão que já cabe no tema aprovado. Uma
**consulta** leva impasse que o grupo não deve resolver sozinho, sempre
com o problema medido, o que já se tentou e as saídas com custo. As duas
são curtas: o diagnóstico longo mora em
[artigo/decisoes-metodologicas.md](artigo/decisoes-metodologicas.md).

### [`briefing.md`](briefing.md)

O documento de contexto original, movido da raiz. É a referência de
última instância: quando esta documentação e o briefing discordarem, o
briefing vence — ou vira uma ADR explicando a divergência.

### [`plano-arquitetura.md`](plano-arquitetura.md)

O plano que o grupo revisou e aprovou, e do qual este repositório é a
execução. Mantido como registro histórico; o estado atual está nos
documentos acima.

## Quando atualizar

- **Mudou um contrato?** ADR + o documento em `contratos/` + fixtures.
- **Fechou uma spec?** Marque `Status: concluída` no arquivo da spec, no
  mesmo PR.
- **Tomou uma decisão não-óbvia?** Se ela puder surpreender quem ler o
  repositório depois, vira ADR ou entra em
  `artigo/decisoes-metodologicas.md`.
- **Gerou figura ou tabela?** Confira que entrou nos índices.
