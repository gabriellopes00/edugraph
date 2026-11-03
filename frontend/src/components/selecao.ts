/**
 * Destaque do nó escolhido — ADR-0013.
 *
 * Ao clicar num aluno, o grafo precisa dizer "é este, e estes são os
 * laços dele": o nó cresce e ganha um halo, as ligações dele ficam grossas
 * e na cor de destaque (quanto mais peso, mais grossa), os vizinhos ficam
 * com contorno e só os mais fortes mostram o nome; o resto esmaece. A
 * câmera então enquadra o aluno com os vizinhos, para ele não se perder
 * numa rede com dezenas de nós.
 *
 * Só classes e estilo: nada aqui refaz o grafo. Serve ao laboratório e ao
 * explorador, que têm Cytoscapes diferentes.
 */

import type cytoscape from "cytoscape";
import type { Collection, Core, EdgeSingular, NodeCollection, NodeSingular, StylesheetJson } from "cytoscape";

/** Classes que `destacarSelecao` põe e que quem limpa o grafo precisa tirar. */
export const CLASSES_DA_SELECAO = "laco laco-vizinho vizinho";

/** Quantos vizinhos mostram o nome: os de ligação mais forte. */
const MAX_VIZINHOS_ROTULADOS = 12;

/** O nó escolhido fica tantas vezes maior que o normal. */
const FATOR_DO_NO_ESCOLHIDO = 1.9;

const movimentoReduzido = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/**
 * Marca o nó `id`, as ligações visíveis dele e os vizinhos; esmaece o resto.
 *
 * Ignora o que está oculto (`.oculto`: no laboratório, as disciplinas e as
 * matrículas somem na projeção, mas continuam no Cytoscape).
 *
 * @returns o nó com os vizinhos, para enquadrar; `null` se o nó não existe.
 */
export function destacarSelecao(cy: Core, id: string, classeRotulo: string): Collection | null {
  const alvo = cy.getElementById(id);
  if (alvo.empty()) return null;
  alvo.select();
  const lacos = alvo.connectedEdges().not(".oculto");
  const vizinhos = lacos.connectedNodes().not(alvo);
  const entreVizinhos = vizinhos.edgesWith(vizinhos).not(".oculto");

  lacos.addClass("laco");
  entreVizinhos.addClass("laco-vizinho");
  vizinhos.addClass("vizinho");

  const maisFortes = lacos
    .sort((a, b) => Number(b.data("weight")) - Number(a.data("weight")))
    .slice(0, MAX_VIZINHOS_ROTULADOS);
  maisFortes.connectedNodes().not(alvo).addClass(classeRotulo);

  const grupo = alvo.union(vizinhos);
  cy.elements().not(grupo).not(lacos).not(entreVizinhos).addClass("apagado");
  return grupo;
}

/**
 * Enquadra `grupo` com folga, sem passar de `zoomMaximo` (um aluno com um
 * vizinho só não vira um ponto gigante).
 */
export function enquadrarGrupo(cy: Core, grupo: Collection | NodeCollection, zoomMaximo: number, duracaoMs = 420): void {
  const caixa = grupo.boundingBox({});
  const padding = cy.width() < 600 ? 40 : 90;
  const nivel = Math.max(
    cy.minZoom(),
    Math.min(
      cy.maxZoom(),
      zoomMaximo,
      (cy.width() - 2 * padding) / Math.max(caixa.w, 1),
      (cy.height() - 2 * padding) / Math.max(caixa.h, 1),
    ),
  );
  const pan = {
    x: cy.width() / 2 - nivel * (caixa.x1 + caixa.w / 2),
    y: cy.height() / 2 - nivel * (caixa.y1 + caixa.h / 2),
  };
  cy.stop();
  if (movimentoReduzido()) cy.viewport({ zoom: nivel, pan });
  else cy.animate({ zoom: nivel, pan }, { duration: duracaoMs, easing: "ease-in-out" });
}

interface OpcoesDeEstilo {
  /** Cor de destaque (o `--focus` do tema). */
  destaque: string;
  /** Pixels de tela convertidos em unidades do grafo, para a linha não engrossar com o zoom. */
  px: (n: number) => () => number;
  zoom: () => number;
  /** Peso da ligação normalizado em [0, 1]. */
  relativo: (e: EdgeSingular) => number;
  /** Rótulo do nó: o painel já o mostra; o grafo só precisa do nome. */
  classeRotulo: string;
}

/** Regras de estilo da seleção; vão **depois** das regras de `.apagado`. */
export function estiloDaSelecao(o: OpcoesDeEstilo): StylesheetJson {
  const peso = (e: EdgeSingular) => Math.min(Math.max(o.relativo(e), 0), 1);
  const grande = (n: NodeSingular) => Number(n.data("size")) * FATOR_DO_NO_ESCOLHIDO;
  return [
    {
      selector: "edge.laco-vizinho",
      style: { opacity: 0.18, "z-index": 5 } as unknown as cytoscape.Css.Edge,
    },
    {
      selector: "edge.laco",
      style: {
        "line-color": o.destaque,
        width: (e: EdgeSingular) => (2 + peso(e) * 4.5) / Math.max(o.zoom(), 0.01),
        opacity: (e: EdgeSingular) => 0.55 + peso(e) * 0.4,
        "z-index": 25,
      } as unknown as cytoscape.Css.Edge,
    },
    {
      selector: "node.vizinho",
      style: {
        "border-color": o.destaque,
        "border-width": o.px(2.4),
        "z-index": 12,
        "text-opacity": 1,
      } as unknown as cytoscape.Css.Node,
    },
    {
      selector: `node.${o.classeRotulo}`,
      style: { label: "data(label)", "min-zoomed-font-size": 0 } as unknown as cytoscape.Css.Node,
    },
    {
      selector: "node:selected",
      style: {
        width: grande,
        height: grande,
        label: "data(label)",
        "min-zoomed-font-size": 0,
        "font-size": o.px(14),
        "font-weight": 700,
        "text-margin-y": o.px(10),
        "border-color": o.destaque,
        "border-width": o.px(3),
        "outline-color": o.destaque,
        "outline-width": o.px(3),
        "outline-offset": o.px(3),
        "outline-opacity": 0.55,
        "underlay-color": o.destaque,
        "underlay-opacity": 0.22,
        "underlay-padding": o.px(12),
        "underlay-shape": "ellipse",
        "z-index": 40,
        "transition-property": "width, height, background-color, opacity",
        "transition-duration": 260,
      } as unknown as cytoscape.Css.Node,
    },
  ];
}
