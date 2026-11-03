/**
 * Quadros da animação do laboratório — ADR-0013.
 *
 * A tela conta a montagem em quatro etapas: **matrículas** (o grafo
 * bipartido), **projeção** (só alunos, ligados por disciplinas em
 * comum), **algoritmo** (Louvain ou Girvan–Newman, movimento a
 * movimento) e **resultado**. Este arquivo transforma a resposta de
 * `POST /lab/run` numa lista de quadros e diz, para cada quadro, o que
 * está visível e de que cor cada nó é.
 *
 * Tudo aqui é função pura, sem DOM: o estado de um quadro depende só do
 * quadro. É isso que deixa o controle deslizante andar para trás, e o
 * que permite testar a animação sem navegador (`tests/frames.test.mjs`).
 * Só `import type`: o teste transpila este arquivo isolado.
 */

import type { LabRun } from "../types";

export type Etapa = "matriculas" | "projecao" | "algoritmo" | "resultado";

export const ETAPAS: { id: Etapa; nome: string }[] = [
  { id: "matriculas", nome: "Matrículas" },
  { id: "projecao", nome: "Projeção" },
  { id: "algoritmo", nome: "Algoritmo" },
  { id: "resultado", nome: "Resultado" },
];

export interface Quadro {
  etapa: Etapa;
  /** Posição dentro da etapa, de 0 a `n - 1`. */
  i: number;
  n: number;
}

/** Limites de quadros por etapa: acima disso, cada quadro mostra mais de um item. */
const MAX_QUADROS_MATRICULAS = 40;
const MAX_QUADROS_PROJECAO = 36;
const MAX_QUADROS_REMOCAO = 70;

export function montarQuadros(run: LabRun): Quadro[] {
  const quadros: Quadro[] = [];
  const empilhar = (etapa: Etapa, n: number) => {
    for (let i = 0; i < n; i++) quadros.push({ etapa, i, n });
  };

  empilhar("matriculas", Math.max(1, Math.min(run.bipartite.edges.length, MAX_QUADROS_MATRICULAS)));
  empilhar("projecao", Math.max(1, Math.min(run.projection.edges.length, MAX_QUADROS_PROJECAO)));

  if (run.louvain) {
    empilhar("algoritmo", run.louvain.moves.length + 1);
  } else if (run.girvan_newman) {
    const quadrosDeRemocao = Math.min(remocoesAteOMelhor(run), MAX_QUADROS_REMOCAO);
    empilhar("algoritmo", quadrosDeRemocao + 1);
  }
  empilhar("resultado", 1);
  return quadros;
}

/** Quantas arestas o Girvan–Newman removeu até o corte de maior Q. */
export function remocoesAteOMelhor(run: LabRun): number {
  const gn = run.girvan_newman;
  if (!gn) return 0;
  if (gn.best < 0) return gn.removed.length;
  return gn.splits[gn.best].n_removed;
}

/** Estado visível de um quadro. */
export interface Estado {
  etapa: Etapa;
  /** Arestas do bipartido já desenhadas. */
  matriculas: number;
  /** Arestas da projeção já desenhadas. */
  projecao: number;
  /** Girvan–Newman: arestas já removidas. */
  removidas: number;
  /** Índices (em `removed`) das removidas neste quadro: piscam em vermelho. */
  recemRemovidas: number[];
  /** Nó → id do grupo exibido agora; `null` = sem cor por grupo. */
  grupos: Record<string, number> | null;
  q: number | null;
  /** Quantos grupos há agora. */
  k: number | null;
  /** Louvain: movimentos feitos. Girvan–Newman: arestas removidas. */
  passo: number;
  total: number;
}

const ate = (i: number, n: number, total: number) =>
  Math.min(total, Math.ceil(((i + 1) * total) / Math.max(n, 1)));

/** Q da partição com cada nó sozinho: `−Σ (k_i / 2m)²`. É de onde o Louvain parte. */
export function qDoInicio(run: LabRun): number {
  const forca = new Map<string, number>();
  let dois_m = 0;
  for (const e of run.projection.edges) {
    forca.set(e.source, (forca.get(e.source) ?? 0) + e.weight);
    forca.set(e.target, (forca.get(e.target) ?? 0) + e.weight);
    dois_m += 2 * e.weight;
  }
  if (dois_m === 0) return 0;
  let soma = 0;
  for (const k of forca.values()) soma += (k / dois_m) ** 2;
  return -soma;
}

function louvainApos(run: LabRun, movimentos: number): Record<string, number> {
  const trace = run.louvain!;
  const grupos: Record<string, number> = {};
  trace.nodes.forEach((id, indice) => {
    grupos[id] = indice;
  });
  for (let j = 0; j < movimentos; j++) {
    const { members, to } = trace.moves[j];
    for (const indice of members) grupos[trace.nodes[indice]] = to;
  }
  return grupos;
}

const contar = (grupos: Record<string, number>) => new Set(Object.values(grupos)).size;

export function estadoDoQuadro(run: LabRun, quadro: Quadro): Estado {
  const base: Estado = {
    etapa: quadro.etapa,
    matriculas: 0,
    projecao: 0,
    removidas: 0,
    recemRemovidas: [],
    grupos: null,
    q: null,
    k: null,
    passo: 0,
    total: 0,
  };
  const totalMatriculas = run.bipartite.edges.length;
  const totalProjecao = run.projection.edges.length;

  if (quadro.etapa === "matriculas") {
    return { ...base, matriculas: ate(quadro.i, quadro.n, totalMatriculas) };
  }
  const comProjecao = { ...base, matriculas: totalMatriculas };
  if (quadro.etapa === "projecao") {
    return { ...comProjecao, projecao: ate(quadro.i, quadro.n, totalProjecao) };
  }
  const cheia = { ...comProjecao, projecao: totalProjecao };

  if (quadro.etapa === "resultado") {
    return {
      ...cheia,
      grupos: run.result.membership,
      q: run.result.q,
      k: run.result.n_communities,
      passo: run.louvain ? run.louvain.moves.length : remocoesAteOMelhor(run),
      total: run.louvain ? run.louvain.moves.length : remocoesAteOMelhor(run),
    };
  }

  if (run.louvain) {
    const movimentos = quadro.i;
    const grupos = louvainApos(run, movimentos);
    return {
      ...cheia,
      grupos,
      q: movimentos > 0 ? run.louvain.moves[movimentos - 1].q : qDoInicio(run),
      k: contar(grupos),
      passo: movimentos,
      total: run.louvain.moves.length,
    };
  }

  const gn = run.girvan_newman!;
  const total = remocoesAteOMelhor(run);
  const quadrosDeRemocao = Math.max(quadro.n - 1, 1);
  const alvo = (i: number) => Math.round((i * total) / quadrosDeRemocao);
  const removidas = quadro.n === 1 ? total : alvo(quadro.i);
  const anteriores = quadro.i > 0 ? alvo(quadro.i - 1) : 0;
  const recemRemovidas: number[] = [];
  for (let j = anteriores; j < removidas; j++) recemRemovidas.push(j);

  // Corte vigente: o último que já apareceu e que tem a partição completa.
  let corte = -1;
  for (let s = 0; s < gn.splits.length; s++) {
    if (gn.splits[s].n_removed <= removidas && gn.splits[s].membership) corte = s;
    if (gn.splits[s].n_removed > removidas) break;
  }
  const atual = corte >= 0 ? gn.splits[corte] : null;
  return {
    ...cheia,
    removidas,
    recemRemovidas,
    grupos: atual ? atual.membership : null,
    q: atual ? atual.q : null,
    k: atual ? atual.k : 1,
    passo: removidas,
    total,
  };
}

/** Posição de cada grupo na ordem de tamanho (0 = maior), como na legenda. */
export function ordemPorTamanho(grupos: Record<string, number>): Map<number, number> {
  const tamanhos = new Map<number, number>();
  for (const g of Object.values(grupos)) tamanhos.set(g, (tamanhos.get(g) ?? 0) + 1);
  const ordenados = [...tamanhos.entries()].sort((a, b) => b[1] - a[1] || a[0] - b[0]);
  return new Map(ordenados.map(([g], posicao) => [g, posicao]));
}

/**
 * Índice de cor de cada nó. Um grupo exibido recebe a cor do grupo do
 * resultado a que a maioria dos seus nós vai pertencer: a cor não pisca
 * quando o grupo cresce, e um grupo que se funde a outro já tem a cor
 * do destino. Grupo de um nó só fica sem cor (`null`) durante a
 * animação — ele ainda não é "grupo" de ninguém.
 */
export function indicesDeCor(
  exibidos: Record<string, number>,
  finais: Record<string, number>,
  colorirUnitarios: boolean,
): Record<string, number | null> {
  const ordem = ordemPorTamanho(finais);
  const porGrupo = new Map<number, string[]>();
  for (const [no, g] of Object.entries(exibidos)) {
    const lista = porGrupo.get(g) ?? [];
    lista.push(no);
    porGrupo.set(g, lista);
  }
  const resultado: Record<string, number | null> = {};
  for (const nos of porGrupo.values()) {
    let indice: number | null = null;
    if (nos.length > 1 || colorirUnitarios) {
      const votos = new Map<number, number>();
      for (const no of nos) {
        const final = finais[no];
        if (final !== undefined) votos.set(final, (votos.get(final) ?? 0) + 1);
      }
      let melhor = -1;
      for (const [final, n] of [...votos.entries()].sort((a, b) => a[0] - b[0])) {
        if (n > melhor) {
          melhor = n;
          indice = ordem.get(final) ?? null;
        }
      }
    }
    for (const no of nos) resultado[no] = indice;
  }
  return resultado;
}

/** Pontos do gráfico de Q: Louvain, por movimento; Girvan–Newman, por número de grupos. */
export interface SerieQ {
  eixoX: string;
  pontos: { x: number; y: number }[];
  /** Índice, em `pontos`, do melhor corte (só Girvan–Newman). */
  melhor: number | null;
}

export function serieQ(run: LabRun): SerieQ {
  if (run.louvain) {
    const pontos = [{ x: 0, y: qDoInicio(run) }];
    run.louvain.moves.forEach((m, i) => pontos.push({ x: i + 1, y: m.q }));
    return { eixoX: "movimentos", pontos, melhor: null };
  }
  const gn = run.girvan_newman!;
  return {
    eixoX: "grupos",
    pontos: gn.splits.map((s) => ({ x: s.k, y: s.q })),
    melhor: gn.best >= 0 ? gn.best : null,
  };
}

/** Índice, em `serieQ().pontos`, do ponto que corresponde ao estado atual. */
export function pontoAtual(run: LabRun, estado: Estado): number {
  if (run.louvain) return estado.passo;
  const gn = run.girvan_newman!;
  let atual = -1;
  for (let s = 0; s < gn.splits.length; s++) {
    if (gn.splits[s].n_removed <= estado.removidas) atual = s;
    else break;
  }
  return atual;
}

/** Quanto o quadro dura na tela, em ms, na velocidade 1×. */
export function duracaoDoQuadro(run: LabRun, quadro: Quadro): number {
  const ultimo = quadro.i === quadro.n - 1;
  switch (quadro.etapa) {
    case "matriculas":
      return ultimo ? 900 : 45;
    case "projecao":
      return ultimo ? 1000 : 50;
    case "algoritmo": {
      const lento = run.louvain ? 120 : 90;
      return ultimo ? 1300 : quadro.i === 0 ? 900 : lento;
    }
    default:
      return 0;
  }
}
