# ADR-0014: Dividir o trabalho por frente, não por pessoa

**Status:** aceita (detalha a ADR-0013 e diverge da seção 5 do briefing)
**Data:** 2026-11-04
**Decidido por:** o grupo
**Frente:** [T]

## Contexto

Na fase de arquitetura, cada frente tinha um dono, e o repositório
refletia isso: specs com "Dono", observações em `para-<pessoa>.md`, ADRs
assinadas pelos três, e a regra de identificar quem estava trabalhando
antes de qualquer tarefa. Desde a ADR-0013 (30/10/2026), qualquer parte do
sistema pode ser alterada em qualquer tarefa, e a divisão por pessoa
deixou de corresponder a como o trabalho acontece: a mesma sessão mexe nas
três frentes, e as observações passaram a ser "de Fulano para Fulano"
sobre código que os dois alteram.

## Decisão

O projeto se organiza **só por frente**. As frentes A (dados e
modelagem), B (comunidades) e C (centralidade e aplicação) continuam
dividindo o código, as specs, as observações e a fronteira de import
(ADR-0003); ninguém é dono de uma frente. Documentação, specs, ADRs,
observações e comentários atribuem autoria e pendência à frente ou ao
grupo, nunca a um integrante. Os nomes aparecem só como autoria do TCC.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Manter o dono por frente | Não descreve mais o trabalho; obriga a perguntar "quem é você" antes de cada tarefa e gera recado entre pessoas sobre código comum |
| Abolir as frentes também | A fronteira de import e as três regras dos testes de contrato dependem delas; as specs e as tabelas do artigo estão organizadas assim |

## Consequências

**Boas.** Qualquer integrante pega qualquer pendência pelo arquivo da
frente; o `CLAUDE.md` deixa de depender de identificar a pessoa.

**Ruins.** As observações antigas perdem a informação de quem escreveu;
quem precisar dela recorre ao histórico do git. O `briefing.md` e o
`plano-arquitetura.md`, registros históricos, continuam citando os donos
originais.

**O que muda no código.** `observacoes/para-<pessoa>.md` passam a
`para-frente-a.md`, `para-frente-b.md` e `para-frente-c.md`; a linha
"Dono" sai das specs; "Decidido por" das ADRs vira "o grupo"; docstrings
das frentes deixam de citar nomes. Nenhum teste muda.

## Impacto no artigo

Nenhum. A divisão em frentes continua descrita no capítulo de método;
a autoria do trabalho não muda.
