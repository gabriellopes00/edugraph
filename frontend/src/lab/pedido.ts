/**
 * Comparação de pedidos do laboratório — ADR-0013.
 *
 * O laboratório só monta a rede quando o visitante aperta ▶, e pode
 * mudar vários controles antes disso. Estas funções dizem se o que está
 * nos controles já é o que está na tela. Puras e sem imports de execução:
 * o teste transpila só este arquivo.
 */

import type { LabRequest } from "../types";

/** Identifica a turma, sem o algoritmo: duas rodadas com a mesma chave são comparáveis. */
export const chaveDaTurma = (r: LabRequest): string =>
  [r.source, r.students, r.seed, r.noise, r.side, r.weighting, r.min_weight].join("|");

/** Dois pedidos iguais em tudo o que muda o resultado. */
export function mesmoPedido(a: LabRequest, b: LabRequest): boolean {
  return chaveDaTurma(a) === chaveDaTurma(b) && a.algorithm === b.algorithm && a.time_budget_s === b.time_budget_s;
}

/** Mesma turma e mesma rede, só o corte de ligações (ou o algoritmo) pode ter mudado. */
export function mesmaBase(a: LabRequest, b: LabRequest): boolean {
  return chaveDaTurma({ ...a, min_weight: null }) === chaveDaTurma({ ...b, min_weight: null });
}

/**
 * O que o botão ▶ vai fazer: montar a rede (nada na tela, ou os controles
 * mudaram desde a última montagem) ou só tocar e pausar a animação.
 */
export function acaoDoTocar(montado: LabRequest | null, atual: LabRequest): "montar" | "tocar" {
  return montado === null || !mesmoPedido(montado, atual) ? "montar" : "tocar";
}
