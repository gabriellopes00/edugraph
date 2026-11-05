"""Frente C — Centralidade e Aplicação  ``[C]``.

Grau, intermediação (Brandes) e autovetor (iteração de potência), nas
duas projeções; identificação das disciplinas críticas; API e front-end.

**Produz** ``centrality/``, ``metrics/centrality_top.csv``, a API e a
página de visualização. **Consome** ``projections/``, ``communities/`` e
os próprios ``centrality/``.

A aplicação sobre os nós de **disciplina** é obrigatória (briefing §6.2
e §13): é ela que responde à parte do objetivo declarado sobre gargalos
no fluxo curricular. Ver :mod:`~edugraph.centrality.critical_disciplines`.

Fronteira (ADR-0003): este subpacote não importa ``edugraph.data`` nem
``edugraph.community``. As partições que o front colore chegam pelo
disco, e a API não sabe se vieram da Frente B ou da fixture.
"""
