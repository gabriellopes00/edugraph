# ADR-0002: Artefatos como bundle CSV + `meta.json`, com `schema_version`

**Status:** aceita
**Data:** 2026-09-17
**Decidido por:** o grupo
**Frente:** [T]

## Contexto

Decidida a fronteira em disco (ADR-0001), falta escolher o formato. O
starter kit usa GML: para 120 nós e 1.971 arestas, o arquivo tem 10.577
linhas, e os tipos são inferidos na leitura — um peso inteiro volta como
inteiro, um peso fracionário como float, e o código de quem lê precisa
lidar com os dois.

A stack definida no briefing (§7) admite "arquivos (GML/Parquet) ou
SQLite".

## Decisão

Cada artefato é um diretório com uma lista de arestas em CSV mais um
`meta.json`. O `meta.json` carrega `schema_version`, a especificação que
gerou o artefato, quem o produziu e quando. Mudar layout, nome de coluna
ou semântica de campo exige subir `SCHEMA_VERSION` **e** uma ADR.

A escrita é canônica: nós e arestas ordenados, extremos de aresta em
ordem lexicográfica, floats no `repr` mais curto que retorna ao mesmo
valor, quebra de linha `\n` e UTF-8 explícito.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| GML (starter kit) | Verboso (5× o volume), tipos inferidos na leitura, não abre no pandas nem no front-end sem conversão |
| GraphML | Mesmas objeções do GML, com XML por cima |
| Parquet | Compacto e tipado, mas binário: perde-se a inspeção por `cat` e o diff legível em PR, que é o que torna a fixture versionada útil |
| SQLite | Um arquivo binário compartilhado entre três pessoas é conflito de merge garantido |

## Consequências

**Boas.** Uma linha por aresta. Abre no pandas, no Excel e no front-end.
O `meta.json` é o que o artigo cita quando precisa dizer com que
parâmetros um número foi obtido. A escrita canônica faz de
`escrever → ler → escrever` uma identidade byte a byte, o que permite
versionar fixtures sem diff espúrio e torna um diff em `data/fixtures/`
um sinal confiável de que algo mudou de verdade.

**Ruins.** CSV ocupa mais espaço que Parquet e é mais lento de ler em
escala. Para os tamanhos deste trabalho (dezenas de milhares de arestas
por projeção depois dos cortes da spec A-06), não é gargalo. Exportar GML
ou GraphML para o Gephi continua disponível como **conveniência**, nunca
como contrato.

**O que muda no código.** `contracts/io.py` e `contracts/paths.py`;
`tests/contract/test_roundtrip.py` verifica round-trip e estabilidade
byte a byte.

## Impacto no artigo

Nenhum diretamente. Indiretamente: é o que permite afirmar que os
resultados são reprodutíveis, porque cada artefato carrega a
especificação que o gerou.
