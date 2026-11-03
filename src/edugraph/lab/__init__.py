"""Laboratório ao vivo  ``[T]`` — monta o grafo na frente de quem avalia.

Pacote transversal, como ``reporting``: reúne a geração de uma turma de
demonstração, a projeção, o Louvain e o Girvan-Newman **com rastro do
passo a passo**, e a leitura dos resultados em linguagem de gente (nomes
de comunidades, papéis dos nós, frases-resumo).

Ele não pertence a nenhuma das frentes: chama as três pelo registro
(``contracts.registry``) e pelos módulos que cada uma expõe. A API
(``edugraph.api``) importa este pacote, e não as frentes — a fronteira
da ADR-0003 continua valendo. A troca da "API somente leitura" pelo
laboratório está na ADR-0013.

Tudo aqui é Teoria dos Grafos: nenhum modelo é treinado (CLAUDE.md,
regra 1). Os nomes e os papéis saem de contagens e limiares fixos.
"""
