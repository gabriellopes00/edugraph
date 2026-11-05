# Branches, merge e revisão

Decisão registrada na [ADR-0009](../adr/ADR-0009-trunk-based-prs-por-spec.md).

## O fluxo

- **`main` protegida**: só entra por PR com CI verde. Sem branches de
  frente de longa duração.
- **Uma spec, um branch, um PR**: `a/A-04-projecao-manual`,
  `b/B-02-girvan-newman`, `c/C-04-api`.
- **Rebase** sobre `main` antes de abrir o PR; **squash merge**.
- PRs pequenos, idealmente fechados no mesmo dia.
- Commits em português, com o id da spec no título:
  `B-03: modularidade à mão e comparação com NetworkX`.

## Quem revisa o quê

**PR que toca só uma frente** — `src/<frente>/`, `tests/<frente>/`,
`docs/specs/frente-X/`: mescla com CI verde. Revisão opcional.

**PR que toca área compartilhada** — `contracts/`, `tests/contract/`,
`data/fixtures/`, `__main__.py`, `pyproject.toml`, `requirements*.txt`:
**aprovação no PR**. Se muda contrato, ADR no mesmo PR.

A assimetria é proposital: 90% dos PRs caem no primeiro caso e não
esperam ninguém; os 10% que podem quebrar as outras frentes são
revisados.

## Por que o conflito é raro aqui

Três coisas, nesta ordem de importância:

1. **Cada pessoa toca pastas diferentes** (ADR-0003). É a arquitetura
   trabalhando a favor do processo.
2. **Fixtures nunca mudam.** Nova versão é nova pasta. Isso elimina a
   classe inteira de conflitos "a fixture mudou e meu teste quebrou".
3. **Arquivos compartilhados de escrita frequente são gerados, não
   editados.** O índice de figuras e o de tabelas saem de
   `python -m edugraph figures --index`, não da mão de três pessoas.

## O que a CI verifica em cada PR

```bash
ruff check .            # lint
ruff format --check .   # formatação
mypy src/edugraph/contracts   # tipagem estrita nos contratos
pytest -m "not slow"    # a suíte, sem Girvan-Newman completo nem OULAD inteiro
```

Verde é condição para mesclar. Os testes de contrato são os que importam
mais aqui: eles é que garantem que o PR de uma frente não quebrou outra.

## Situações específicas

**Preciso mudar um contrato.** Abra a discussão antes de escrever código.
O caminho é: ADR → `SCHEMA_VERSION` nova → validador atualizado →
fixtures regeneradas, tudo num PR só, aprovado pelos três. Antes disso,
confira se o que você precisa não cabe em `params` ou em `meta.stats` —
ver [o fim do README de contratos](../contratos/README.md).

**Minha spec ficou grande demais para um PR.** Quebre a spec, não o PR.
As specs foram dimensionadas para uma sessão de trabalho justamente por
isso (briefing §12); se uma passou do tamanho, ela estava mal
dimensionada.

**Preciso de algo que está em outra frente.** Não importe. Ou o que
você precisa é contrato (e vai para `contracts/`), ou é utilidade
genérica (e vai para `reporting/`), ou o código pertence a outra
frente. O teste de fronteira vai recusar de qualquer forma.

**A CI quebrou num teste `xfail`.** Um `xfail(strict=True)` que **passa**
quebra a CI de propósito: é o aviso de que a spec fechou e o marcador
pode sair. Remova o `@pytest.mark.xfail` no mesmo PR.
