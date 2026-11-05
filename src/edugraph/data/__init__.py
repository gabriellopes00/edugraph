"""Frente A — Dados e Modelagem  ``[A]``.

ETL do OULAD, gerador sintético, construção do grafo bipartido e as duas
projeções ponderadas.

**Produz** ``bipartite/``, ``projections/``, ``bipartite/outcomes.csv`` e
``metrics/projections.csv``. **Consome** apenas CSV bruto.

Fronteira (ADR-0003): este subpacote não importa ``edugraph.community``,
``edugraph.centrality`` nem ``edugraph.api``. Um teste de contrato falha
se isso mudar.
"""
