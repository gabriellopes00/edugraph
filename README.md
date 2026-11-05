# edugraph

**Análise Topológica e Detecção de Comunidades em Redes Complexas:
Projeção de Grafos Bipartidos e Métricas de Centralidade em Dados
Educacionais**

TCC — Ciência da Computação, Centro Universitário Padre Anchieta
(UniAnchieta), Jundiaí/SP.
**Grupo 16:** Gabriel Luís Lopes, Pedro Alexandre dos Santos Chaves,
Lucas Timponi Mercadante Castro.
**Orientador:** Prof. Me. Clayton Augusto Valdo.

Modela dados educacionais como um grafo bipartido aluno↔disciplina,
projeta em grafos monopartidos ponderados, detecta comunidades e mede
centralidade — **usando apenas algoritmos de Teoria dos Grafos, sem
aprendizado de máquina**.

---

## Comece aqui

**Um comando só:** depois do clone, `python scripts/iniciar.py` cria a
`.venv`, instala, valida as fixtures, roda os testes da CI, compila a
interface (se houver Node) e abre http://127.0.0.1:8000/ no navegador.
Num clone limpo leva ~2 min; nas vezes seguintes, segundos.

```bash
git clone https://github.com/luctmc/TCC.bipartite-network-analysis C:\tcc
cd C:\tcc
python scripts/iniciar.py                 # --sem-testes pula o pytest; --porta 8001 troca a porta
```

Passo a passo, se preferir:

```bash
git clone https://github.com/luctmc/TCC.bipartite-network-analysis
cd TCC.bipartite-network-analysis

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

pip install -e ".[dev]"
```

**Windows:** clone numa pasta de caminho curto (por exemplo
`C:\tcc\`). O caminho mais longo do repositório tem 93 caracteres, e o
Windows recusa arquivos acima de 260; numa pasta funda, o `git clone`
termina com `Filename too long` e a árvore fica incompleta. Se não der
para encurtar, rode antes `git config --global core.longpaths true`.

Confira que está tudo de pé:

```bash
python -m edugraph validate --root data/fixtures
pytest -m "not slow"        # ~20 s: o que a CI roda
pytest                      # ~1 min: inclui o Girvan-Newman completo
```

Esperado: os três datasets de fixture validando. Em 30/10/2026, num
clone limpo (Windows 11, Python 3.14), `pytest -m "not slow"` retornou
**358 testes passando, 1 pulado e 1 desmarcado** em 17 s, e `pytest`
inteiro, **359 passando e 1 pulado** em 59 s. O teste pulado depende de
`oulad_module_presentation`, que só existe depois do download do OULAD.
Há 1 aviso de depreciação do TestClient/HTTPX, sem efeito.

Requer **Python 3.11+** (a CI roda 3.11 e 3.13). O front-end requer
**Node 20 (>=20.19), 22 (>=22.13) ou >=24** (ESLint 10), e é opcional:
a análise inteira funciona sem ele. Sem o front compilado, `GET /`
responde um JSON explicando como gerá-lo; a API e `/docs` funcionam.

## Caminho rápido: só o sintético

**Nada do OULAD é necessário** para ver o sistema funcionando. Os resultados
do OULAD (`data/processed/`) levam horas para gerar e ficam fora do git; sem
essa pasta o sistema simplesmente não lista esses datasets. O que roda sem
eles, em poucos minutos:

```bash
python -m edugraph validate --root data/fixtures   # artefatos de fixture
pytest -m "not slow"                               # a suíte (o teste do OULAD é pulado)
python -m edugraph api serve                       # sem --root: usa data/fixtures
```

Com o front compilado, **http://127.0.0.1:8000/** abre o laboratório, que
gera a turma de Computação na hora (dados fictícios, 0,2 a 3 s por rodada),
e o explorador, com `synthetic_v1`, `synthetic_v2` e `tiny_v1`. Se existir
`data/processed/` (por exemplo, o ZIP de resultados do OULAD descompactado
na raiz do repositório), ele entra sozinho na lista, sem flag nenhuma.
Coberto por `tests/api/test_raiz_ausente.py`.

**Recebeu o ZIP com os resultados do OULAD?** Não precisa baixar nem
recalcular nada:

```bash
python scripts/iniciar.py --oulad caminho\para\oulad-resultados.zip
```

O script acha os datasets dentro do ZIP em qualquer nível de pasta, copia
para `data/processed/`, valida e abre a interface. À mão: extraia de modo
que exista `data/processed/oulad_vle_bbb_2013j/bipartite/nodes.csv` e suba
a API **a partir da raiz do repositório** (as raízes são relativas à pasta
atual). Detalhes em [`docs/entrega.md`](docs/entrega.md), seção 9.

## O que dá para fazer agora

```bash
# validar todos os artefatos sob uma raiz
python -m edugraph validate --root data/fixtures

# subir a API sobre as fixtures
python -m edugraph api serve --root data/fixtures
#   http://127.0.0.1:8000/health    · sobre que raízes está olhando
#   http://127.0.0.1:8000/datasets  · o que já existe em disco
#   http://127.0.0.1:8000/docs      · a documentação da API

# ver o que o pipeline faria
python -m edugraph run configs/synthetic_v1.toml --dry-run

# rodar o pipeline inteiro (dados → comunidades → centralidade) numa
# pasta descartável: ~70 s, quase todos do Girvan-Newman
python -m edugraph run configs/synthetic_v1.toml --out saida-teste
python -m edugraph validate --root saida-teste

# regenerar as fixtures (byte a byte idênticas)
python scripts/make_fixtures.py --force

# detectar comunidades, caracterizar e comparar (Frente B, pronta)
python -m edugraph community louvain --root data/fixtures \
    --dataset synthetic_v1 --projection student_simple
python -m edugraph community characterize --root data/processed --root data/fixtures \
    --dataset synthetic_v1 --partition louvain__student_simple
python -m edugraph community compare --root data/processed --dataset synthetic_v1

# ver os comandos de cada frente
python -m edugraph data --help
python -m edugraph community --help
python -m edugraph centrality --help
```

As três frentes estão implementadas: as 23 specs de
[`docs/specs/`](docs/specs/README.md) estão fechadas.

## A interface: o grafo se monta na sua frente

Precisa de Node (versão abaixo). Compile uma vez e suba a API:

```bash
cd frontend
npm install
npm run build
cd ..
python -m edugraph api serve --root data/processed --root data/fixtures
```

Abra **http://127.0.0.1:8000/**. Há duas abas:

- **Laboratório ao vivo** (abre primeiro). Gera uma turma de Computação
  (dados fictícios, com áreas plantadas) ou amostra um dataset em disco,
  roda Louvain ou Girvan–Newman **de verdade**, em menos de alguns
  segundos, e conta a montagem em quatro etapas: matrículas → projeção →
  algoritmo, movimento a movimento → resultado. Dá para escolher o número
  de alunos, a mistura entre áreas, projetar alunos ou disciplinas, trocar
  a ponderação, cortar ligações fracas e **sortear outra turma**. **Nada
  roda sozinho:** a rede só é montada quando você aperta ▶, e mudar um
  controle espera o próximo ▶. Na primeira visita, um **tour** de 1
  minuto explica a tela (o botão *Tour* no topo o repete; `?tour` na URL
  o força e `?semtour` o desliga). Espaço toca e pausa; ← e → andam quadro a quadro; **F** (ou o botão
  *Apresentar*) vira tela cheia com letra maior.
- **Explorar resultados** (`#explorar`). Os resultados do OULAD já
  calculados, com comunidades nomeadas ("Módulos BBB · GGG", "Pouco
  engajados"), papel de cada nó, contornos e o desfecho revelado.

No resultado, as comunidades têm nome e o texto diz o que o grafo mostra.
Duas revelações mostram o que o grafo **nunca viu**: as áreas que o
gerador plantou e o desfecho dos alunos (aprovado, reprovado…).

Sem o front compilado, `GET /` responde um JSON; a API e `/docs`
funcionam do mesmo jeito. Detalhes e roteiro de apresentação em
[`frontend/README.md`](frontend/README.md); a decisão em
[ADR-0013](docs/adr/ADR-0013-laboratorio-ao-vivo.md).

## Como o projeto está organizado

Três frentes, trabalhando **ao mesmo tempo**. O que torna isso possível:

1. **A fronteira entre frentes é o disco.** Nenhuma frente importa outra;
   elas se comunicam por artefatos num layout fixo. Um teste falha se
   alguém cruzar a fronteira.
2. **As fixtures são completas.** `data/fixtures/synthetic_v1` já tem
   bipartido, quatro projeções, partições e centralidades. As Frentes B e
   C rodam, testam e sobem a API **sem executar uma linha da Frente A**.
3. **Trocar de fonte é trocar `--root`.** Quando o OULAD estiver em
   `data/processed`, ninguém muda código.

| Frente | Escopo |
|---|---|
| **A** — Dados e Modelagem | ETL do OULAD, gerador sintético, bipartido, projeções |
| **B** — Comunidades | Louvain, Girvan-Newman, modularidade, caracterização |
| **C** — Centralidade e Aplicação | grau, intermediação, autovetor, disciplinas críticas, API, front-end |

```
src/edugraph/
├── contracts/     [T] tipos, io, validadores — CONGELADO
├── data/          [A]  ├── community/   [B]  ├── centrality/  [C]
├── api/           [C]  └── reporting/   [T]
└── __main__.py    [T] a única composição das três frentes
configs/           uma configuração de experimento por arquivo
data/fixtures/     [T] commitado, imutável
docs/              ADRs, contratos, specs, material do artigo
frontend/          [C] React + Vite + Cytoscape.js
```

## A restrição inegociável

**Nenhum componente usa IA, aprendizado de máquina ou qualquer modelo
treinado com dados rotulados.** Foi exigência do orientador e é o
diferencial declarado do trabalho.

Rótulos históricos (o desfecho de cada matrícula) vivem em
`outcomes.csv`, separados do grafo, e entram **apenas** na validação a
posteriori.

Isso não é só uma regra escrita: `tests/contract/test_no_ml.py` varre o
código e as dependências, e `test_outcomes_isolation.py` garante que
nenhum módulo fora de `evaluate.py` lê um rótulo. Quebrar a regra quebra
a CI.

## Os dados

**Base principal:** [OULAD](https://research.stem.open.ac.uk/ouanalyse/dataset/)
(Kuzilek; Hlosta; Zdrahal, 2017). Público e anonimizado. O download é
**passo manual**: `python scripts/download_oulad.py` baixa do espelho do
[UCI ML Repository](https://archive.ics.uci.edu/dataset/349) (o link do
site da OU respondia 404 em 18/09/2026), guarda o zip em `data/raw/` e
extrai as sete tabelas em `data/raw/oulad/`. Depois,
`python -m edugraph data etl`. A pasta é ignorada pelo git.

Não é preciso baixá-lo para trabalhar: `tests/data/oulad_mini/` traz as
sete tabelas em miniatura, com o esquema real.

**Base secundária:** gerador sintético com comunidades plantadas, que
serve de *ground truth* e de fixture.

## Documentação

Comece por [`docs/README.md`](docs/README.md). Os atalhos:

- [Visão geral da arquitetura](docs/arquitetura/visao-geral.md)
- [Como as frentes não se bloqueiam](docs/arquitetura/paralelismo.md)
- [As 23 specs](docs/specs/README.md)
- [As 14 ADRs](docs/adr/README.md)
- [Os contratos de dados](docs/contratos/README.md)
- [Estratégia de testes](docs/testes/estrategia.md)

## Contribuindo

`main` é protegida: só entra por PR com CI verde. Uma spec, um branch, um
PR (`a/A-04-projecao-manual`). Commits em português com o id da spec.
Detalhes em [branches-e-merge.md](docs/arquitetura/branches-e-merge.md).

Antes de abrir o PR:

```bash
ruff check . && ruff format --check . && mypy src/edugraph/contracts && pytest -m "not slow"
```

## Referências

- Kuzilek, J.; Hlosta, M.; Zdrahal, Z. **Open University Learning
  Analytics dataset.** *Scientific Data*, 2017.
- Blondel, V. et al. **Fast unfolding of communities in large networks.**
  *J. Stat. Mech.*, 2008.
- Girvan, M.; Newman, M. **Community structure in social and biological
  networks.** *PNAS*, 2002.
- Brandes, U. **A faster algorithm for betweenness centrality.**
  *J. Math. Sociol.*, 2001.
- Zhou, T. et al. **Bipartite network projection and personal
  recommendation.** *Physical Review E*, 2007.

O starter kit que validou o pipeline ponta a ponta (120 alunos, 7
disciplinas, 197 arestas; Louvain Q ≈ 0,47; Girvan-Newman ~645× mais
lento) foi removido depois de cumprir esse papel — as conclusões dele
estão nas ADRs e os números foram reproduzidos pelas fixtures.
[`reference/README.md`](reference/README.md) registra o que ele mediu, o
que sobreviveu dele no código, e como recuperá-lo do histórico do git.
