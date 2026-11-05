# Observações por frente

Pendências do código, organizadas pela frente a que pertencem: um problema
achado que não dava para corrigir na hora, uma decisão em aberto, algo que
ficou para depois. A divisão é **por assunto, não por pessoa**
([ADR-0014](../docs/adr/ADR-0014-frentes-sem-dono.md)): qualquer integrante
pode pegar e resolver qualquer item.

O `CLAUDE.md` manda ler esta pasta no começo de toda sessão de trabalho e
mantê-la em dia **sem que ninguém peça**: o Claude anota sozinho o que
achar e, antes de cada commit, move para **Resolvidas** toda observação que
a mudança resolver, mesmo que a tarefa fosse outra.

## Os arquivos

| Arquivo | Frente | Código |
|---|---|---|
| [`para-frente-a.md`](para-frente-a.md) | A — Dados e Modelagem | `src/edugraph/data/`, `scripts/` |
| [`para-frente-b.md`](para-frente-b.md) | B — Detecção de Comunidades | `src/edugraph/community/` |
| [`para-frente-c.md`](para-frente-c.md) | C — Centralidade e Aplicação | `src/edugraph/centrality/`, `api/`, `frontend/` |
| [`para-todos.md`](para-todos.md) | transversal | `contracts/`, `lab/`, `__main__.py`, configs, docs e o que envolve mais de uma frente |

## Antes de começar a trabalhar

1. Abra o arquivo das frentes que a tarefa toca e o `para-todos.md`.
2. Veja a seção **Abertas**. Se alguma observação toca no que você vai
   fazer, resolva junto ou registre o que mudou.

## Como deixar uma observação

Acrescente um item na seção **Abertas** do arquivo da frente, no formato
abaixo. O id é a letra da frente (`A`, `B`, `C` ou `T` para todos) seguida
de um número que ainda não foi usado naquele arquivo. O **De** diz de onde
veio o achado (a frente que estava sendo trabalhada, uma auditoria, uma
revisão) — nunca o nome de quem escreveu.

```markdown
### A-OBS-07 · Título curto do problema

- **De:** Frente C · **Data:** 26/09/2026
- **Onde:** `caminho/do/arquivo.py:78`
- **O quê:** o que está errado ou pendente, com a evidência (comando,
  saída, número).
- **Como resolver:** a correção sugerida, se houver.
```

Use caminho e linha sempre que der: é o que permite achar o ponto sem
perguntar.

## Como fechar uma observação

Quem resolve move o item para a seção **Resolvidas** do mesmo arquivo e
acrescenta uma linha no fim dele:

```markdown
- **Resolvida:** 27/09/2026 pela Frente A, commit `abc1234` — o que foi feito.
```

Se a observação não procede, ela também vai para **Resolvidas**, com o
motivo. Não apague itens: o histórico explica decisões na banca.
