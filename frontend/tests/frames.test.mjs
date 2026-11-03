import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import ts from "typescript";

const source = await readFile(new URL("../src/lab/frames.ts", import.meta.url), "utf8");
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
});
const frames = await import(
  `data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`
);

/** Quatro alunos em dois pares (a–b, c–d), ligados fracamente por b–c. */
const nos = ["a", "b", "c", "d"];
const base = {
  bipartite: {
    students: nos.map((id) => ({ id, label: id })),
    disciplines: [{ id: "D1", label: "Algoritmos" }, { id: "D2", label: "Redes" }],
    edges: [["a", "D1", 70], ["b", "D1", 70], ["c", "D2", 70], ["d", "D2", 70], ["b", "D2", 70]],
  },
  projection: {
    nodes: nos.map((id) => ({ id, label: id, kind: "student" })),
    edges: [
      { source: "a", target: "b", weight: 2 },
      { source: "c", target: "d", weight: 2 },
      { source: "b", target: "c", weight: 1 },
    ],
  },
  result: { membership: { a: 0, b: 0, c: 2, d: 2 }, q: 0.35, n_communities: 2 },
};
const louvain = {
  ...base,
  girvan_newman: null,
  louvain: {
    nodes: nos,
    moves: [
      { members: [1], to: 0, q: 0.1, level: 1 },
      { members: [3], to: 2, q: 0.35, level: 1 },
    ],
  },
};
const girvan = {
  ...base,
  louvain: null,
  girvan_newman: {
    nodes: nos,
    removed: [[1, 2], [0, 1]],
    splits: [{ k: 2, q: 0.35, n_removed: 1, membership: { a: 0, b: 0, c: 1, d: 1 } }],
    best: 0,
  },
};

test("os quadros seguem a ordem matrículas, projeção, algoritmo, resultado", () => {
  const quadros = frames.montarQuadros(louvain);
  const ordem = quadros.map((q) => q.etapa).filter((e, i, todos) => e !== todos[i - 1]);
  assert.deepEqual(ordem, ["matriculas", "projecao", "algoritmo", "resultado"]);
  assert.equal(quadros.filter((q) => q.etapa === "algoritmo").length, 3, "movimentos + o ponto de partida");
  assert.equal(quadros.at(-1).etapa, "resultado");
});

test("as matrículas aparecem aos poucos e terminam todas desenhadas", () => {
  const quadros = frames.montarQuadros(louvain).filter((q) => q.etapa === "matriculas");
  const visiveis = quadros.map((q) => frames.estadoDoQuadro(louvain, q).matriculas);
  assert.deepEqual(visiveis, [...visiveis].sort((a, b) => a - b));
  assert.equal(visiveis.at(-1), louvain.bipartite.edges.length);
});

test("na projeção as matrículas já estão todas e as ligações crescem até o total", () => {
  const quadros = frames.montarQuadros(louvain).filter((q) => q.etapa === "projecao");
  const ultimo = frames.estadoDoQuadro(louvain, quadros.at(-1));
  assert.equal(ultimo.matriculas, louvain.bipartite.edges.length);
  assert.equal(ultimo.projecao, louvain.projection.edges.length);
});

test("o Louvain começa com cada aluno sozinho e termina na partição do resultado", () => {
  const quadros = frames.montarQuadros(louvain).filter((q) => q.etapa === "algoritmo");
  const inicio = frames.estadoDoQuadro(louvain, quadros[0]);
  assert.equal(inicio.k, 4);
  assert.equal(inicio.passo, 0);
  assert.ok(inicio.q < 0, "com todos sozinhos, Q é negativo");
  const fim = frames.estadoDoQuadro(louvain, quadros.at(-1));
  assert.equal(fim.k, 2);
  assert.equal(fim.q, 0.35);
  assert.equal(fim.grupos.a, fim.grupos.b);
  assert.notEqual(fim.grupos.a, fim.grupos.c);
});

test("o Girvan–Newman remove as ligações até o melhor corte e o corte aparece no momento certo", () => {
  const quadros = frames.montarQuadros(girvan).filter((q) => q.etapa === "algoritmo");
  const estados = quadros.map((q) => frames.estadoDoQuadro(girvan, q));
  assert.equal(estados[0].removidas, 0);
  assert.equal(estados[0].k, 1);
  assert.equal(estados[0].grupos, null);
  assert.equal(estados.at(-1).removidas, 1, "para no corte de maior Q, não no fim do dendrograma");
  assert.equal(estados.at(-1).k, 2);
  assert.equal(estados.at(-1).q, 0.35);
});

test("cada aresta removida pisca uma única vez", () => {
  const quadros = frames.montarQuadros(girvan).filter((q) => q.etapa === "algoritmo");
  const piscadas = quadros.flatMap((q) => frames.estadoDoQuadro(girvan, q).recemRemovidas);
  assert.deepEqual(piscadas, [0]);
});

test("o resultado mostra a partição final e o Q do algoritmo", () => {
  const quadro = frames.montarQuadros(girvan).at(-1);
  const estado = frames.estadoDoQuadro(girvan, quadro);
  assert.equal(estado.q, girvan.result.q);
  assert.deepEqual(estado.grupos, girvan.result.membership);
});

test("grupo de um nó só fica sem cor durante a animação, e grupo que vai se fundir já tem a cor do destino", () => {
  const exibidos = { a: 0, b: 1, c: 2, d: 3 };
  const finais = { a: 0, b: 0, c: 2, d: 2 };
  const sem = frames.indicesDeCor(exibidos, finais, false);
  assert.deepEqual(Object.values(sem), [null, null, null, null]);
  const com = frames.indicesDeCor(exibidos, finais, true);
  assert.equal(com.a, com.b, "a e b vão para o mesmo grupo e já têm a mesma cor");
  assert.notEqual(com.a, com.c);

  const meio = frames.indicesDeCor({ a: 0, b: 0, c: 2, d: 3 }, finais, false);
  assert.equal(meio.a, meio.b);
  assert.equal(meio.d, null);
});

test("a cor não depende do número que o algoritmo deu ao grupo", () => {
  const finais = { a: 7, b: 7, c: 3, d: 3, e: 3 };
  const cores = frames.indicesDeCor(finais, finais, true);
  assert.equal(cores.c, 0, "o maior grupo fica com a primeira cor");
  assert.equal(cores.a, 1);
});

test("a série de Q do Louvain parte do Q de todos sozinhos e a do Girvan–Newman marca o melhor corte", () => {
  const l = frames.serieQ(louvain);
  assert.equal(l.eixoX, "movimentos");
  assert.equal(l.pontos.length, 3);
  assert.ok(l.pontos[0].y < 0);
  const g = frames.serieQ(girvan);
  assert.equal(g.eixoX, "grupos");
  assert.equal(g.melhor, 0);
});

test("a duração dos quadros é maior no último de cada etapa, para a plateia acompanhar", () => {
  const quadros = frames.montarQuadros(louvain);
  const algoritmo = quadros.filter((q) => q.etapa === "algoritmo");
  assert.ok(frames.duracaoDoQuadro(louvain, algoritmo.at(-1)) > frames.duracaoDoQuadro(louvain, algoritmo[1]));
});
