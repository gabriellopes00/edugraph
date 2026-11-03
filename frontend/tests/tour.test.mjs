import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import ts from "typescript";

async function carregar(caminho) {
  const source = await readFile(new URL(caminho, import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  });
  return import(`data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`);
}

const tour = await carregar("../src/tour/estado.ts");
const pedido = await carregar("../src/lab/pedido.ts");

/** Armazenamento em memória no lugar do localStorage. */
function memoria(inicial = {}) {
  const dados = { ...inicial };
  return {
    getItem: (k) => (k in dados ? dados[k] : null),
    setItem: (k, v) => {
      dados[k] = v;
    },
  };
}

// ---------------------------------------------------------------------
// Primeira visita
// ---------------------------------------------------------------------

test("tour nunca visto aparece e, depois de marcado, não volta", () => {
  const armazem = memoria();
  assert.equal(tour.jaVisto("lab", armazem), false);
  tour.marcarVisto("lab", armazem);
  assert.equal(tour.jaVisto("lab", armazem), true);
});

test("cada tour tem o seu registro: ver o do laboratório não dispensa o do resultado", () => {
  const armazem = memoria();
  tour.marcarVisto("lab", armazem);
  assert.equal(tour.jaVisto("resultado", armazem), false);
  assert.equal(tour.jaVisto("explorador", armazem), false);
});

test("sem armazenamento (janela privada), o tour aparece sempre e marcar não quebra", () => {
  assert.equal(tour.jaVisto("lab", null), false);
  assert.doesNotThrow(() => tour.marcarVisto("lab", null));
  const quebrado = {
    getItem: () => {
      throw new Error("bloqueado");
    },
    setItem: () => {
      throw new Error("bloqueado");
    },
  };
  assert.equal(tour.jaVisto("lab", quebrado), false);
  assert.doesNotThrow(() => tour.marcarVisto("lab", quebrado));
});

test("?tour força e ?semtour desliga", () => {
  assert.deepEqual(tour.opcoesDaUrl("?tour"), { forcar: true, desligar: false });
  assert.deepEqual(tour.opcoesDaUrl("?semtour"), { forcar: false, desligar: true });
  assert.deepEqual(tour.opcoesDaUrl(""), { forcar: false, desligar: false });
});

// ---------------------------------------------------------------------
// Passos
// ---------------------------------------------------------------------

test("passo opcional sem alvo na tela sai da lista; o sem alvo (boas-vindas) fica", () => {
  const passos = [
    { titulo: "abertura" },
    { titulo: "a", alvo: "#a", opcional: true },
    { titulo: "b", alvo: "#b", opcional: true },
    { titulo: "c", alvo: "#c" },
  ];
  const existe = (seletor) => seletor === "#a";
  assert.deepEqual(
    tour.passosVisiveis(passos, existe).map((p) => p.titulo),
    ["abertura", "a", "c"],
  );
});

// ---------------------------------------------------------------------
// Onde cabe o balão (tela 1000×800, balão 300×200, margem 12, folga 16)
// ---------------------------------------------------------------------

const tela = { w: 1000, h: 800 };
const balao = { w: 300, h: 200 };

test("balão vai para o lado preferido quando cabe", () => {
  const alvo = { left: 50, top: 100, width: 200, height: 100 };
  const p = tour.posicionarBalao(alvo, balao, tela, "direita");
  assert.equal(p.lado, "direita");
  assert.equal(p.left, 50 + 200 + 16);
  // centrado na vertical do alvo: 100 + 50 − 100
  assert.equal(p.top, 50);
});

test("sem espaço à direita, o balão passa para a esquerda", () => {
  const alvo = { left: 700, top: 300, width: 280, height: 100 };
  const p = tour.posicionarBalao(alvo, balao, tela, "direita");
  assert.equal(p.lado, "esquerda");
  assert.equal(p.left, 700 - 16 - 300);
});

test("alvo que ocupa a tela toda recebe o balão dentro dele", () => {
  const alvo = { left: 0, top: 0, width: 1000, height: 800 };
  const p = tour.posicionarBalao(alvo, balao, tela, "baixo");
  assert.equal(p.lado, "dentro");
  assert.equal(p.left, 350);
  assert.equal(p.top, 300);
});

test("balão nunca sai da tela, mesmo com o alvo colado na borda", () => {
  const alvo = { left: 0, top: 0, width: 80, height: 40 };
  for (const lado of ["direita", "esquerda", "baixo", "cima", "dentro"]) {
    const p = tour.posicionarBalao(alvo, balao, tela, lado);
    assert.ok(p.left >= 12 && p.left + 300 <= 988, `${lado}: left ${p.left}`);
    assert.ok(p.top >= 12 && p.top + 200 <= 788, `${lado}: top ${p.top}`);
  }
});

test("sem alvo, o balão fica no centro da tela", () => {
  const p = tour.posicionarBalao(null, balao, tela);
  assert.deepEqual(p, { left: 350, top: 300, lado: "centro" });
});

// ---------------------------------------------------------------------
// ▶ monta ou toca (decisão do grupo: mudar controle espera o play)
// ---------------------------------------------------------------------

const base = {
  source: "demo",
  students: 45,
  seed: 12,
  noise: 0.2,
  side: "student",
  weighting: "simple",
  algorithm: "louvain",
  min_weight: null,
  time_budget_s: 20,
};

test("sem nada montado, o play monta a rede", () => {
  assert.equal(pedido.acaoDoTocar(null, base), "montar");
});

test("controles iguais ao que está na tela: o play só toca e pausa", () => {
  assert.equal(pedido.acaoDoTocar(base, { ...base }), "tocar");
});

test("qualquer controle que muda o resultado faz o play montar de novo", () => {
  for (const mudanca of [
    { students: 60 },
    { seed: 99 },
    { noise: 0.4 },
    { side: "discipline" },
    { weighting: "resource_allocation" },
    { algorithm: "girvan_newman" },
    { min_weight: 2 },
    { source: "oulad_vle_bbb_2013j" },
  ]) {
    assert.equal(pedido.acaoDoTocar(base, { ...base, ...mudanca }), "montar", JSON.stringify(mudanca));
  }
});

test("várias mudanças seguidas contam como uma: voltar ao valor anterior cancela o aviso", () => {
  const mexido = { ...base, students: 60, noise: 0.4 };
  assert.equal(pedido.acaoDoTocar(base, mexido), "montar");
  assert.equal(pedido.acaoDoTocar(base, { ...mexido, students: 45, noise: 0.2 }), "tocar");
});

test("a base da rede ignora o corte de ligações, mas não a turma", () => {
  assert.equal(pedido.mesmaBase(base, { ...base, min_weight: 3 }), true);
  assert.equal(pedido.mesmaBase(base, { ...base, side: "discipline" }), false);
  assert.equal(pedido.mesmaBase(base, { ...base, seed: 1 }), false);
});
