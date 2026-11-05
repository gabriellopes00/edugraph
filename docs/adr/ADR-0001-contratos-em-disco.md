# ADR-0001: Contratos em disco como única fronteira entre as frentes

**Status:** aceita
**Data:** 2026-09-17
**Decidido por:** o grupo
**Frente:** [T]

## Contexto

O requisito central do briefing (§4) é que três pessoas trabalhem
**simultaneamente**, não em sequência. Na organização ingênua isso não
funciona: a Frente B (comunidades) e a Frente C (centralidade) precisam
da projeção que a Frente A (dados) produz, e ficariam paradas esperando.

O starter kit é a prova do problema: a sua API (`src/api/main.py`)
importava o módulo de comunidade e o de centralidade diretamente, e cada
script pressupunha que o anterior rodou e deixou um `.gml` num caminho
fixo. Foi escrito por uma pessoa, em sequência, e funcionava — mas
amarrava as três frentes uma na outra.

(O starter kit foi removido do repositório depois de cumprir esse papel;
ver [`../../reference/README.md`](../../reference/README.md).)

## Decisão

As frentes se comunicam **exclusivamente por artefatos em disco**, num
layout fixo (`<root>/<dataset>/<camada>/<id>`), lido e escrito só por
`edugraph.contracts.io` e validado por `edugraph.contracts.validate`.
Nenhuma frente importa outra.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Chamadas diretas entre módulos (starter kit) | É exatamente o acoplamento que o briefing §4.3 manda eliminar; B e C ficariam bloqueadas até A entregar |
| Objetos em memória num pipeline único | Obriga a rodar tudo a cada vez; o Girvan-Newman sozinho inviabiliza |
| Fila de mensagens entre processos | Infraestrutura pesada, proibida pelo briefing §13; não vira parágrafo no artigo |
| Banco de dados compartilhado | Mesma objeção, mais um esquema a versionar e migrar |

## Consequências

**Boas.** Cada frente roda, testa e evolui sozinha desde o dia 0, sobre
fixtures. Trocar da fixture para o OULAD é trocar `--root`. Os artefatos
intermediários ficam inspecionáveis: abrir um CSV e conferir um peso é
uma operação de dois segundos, não uma sessão de depuração. E, como cada
artefato carrega o `meta.json` que o gerou, todo número do artigo é
rastreável até a configuração que o produziu.

**Ruins.** Há custo de serialização entre etapas, e um passo a mais
(gravar, ler) em cada transição. Em troca, ganha-se a capacidade de
retomar o pipeline do meio — que, com o Girvan-Newman em jogo, vale mais
do que o custo. Também é preciso disciplina: a tentação de "só importar
essa função ali" existe, e é por isso que a fronteira é testada
(ADR-0003).

**O que muda no código.** Todo o subpacote `contracts/`; `tests/contract/`
inteiro; a assinatura de todo estágio recebe `roots` e `out`.

## Impacto no artigo

É a figura que abre o capítulo 3 (`docs/arquitetura/diagrama-cap3.md`): a
coluna central do diagrama é o layout de artefatos, e as três frentes só
se tocam através dela.
