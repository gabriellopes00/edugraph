/**
 * Grafo interativo — spec C-05.
 *
 * Cor e forma por comunidade, tamanho por centralidade, destaque da
 * vizinhança do nó selecionado e transição entre projeções preservando a
 * posição dos nós comuns.
 *
 * O Cytoscape é criado uma vez por grafo. Trocar a partição ou a métrica
 * **não** recria nada: só muda `data(color)` / `data(size)` dos nós, e a
 * transição de estilo do próprio Cytoscape anima a mudança — sem
 * recarregar a página e sem refazer o layout.
 *
 * Nota de escala: um grafo de milhares de arestas não renderiza bem. O
 * corte é da API (C-04, `truncation` no corpo); este componente confia
 * no que recebe, simplifica o desenho acima de `MAX_EDGES_CONFORTAVEL` e
 * avisa.
 */

import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from "react";
import cytoscape, { type Core, type ElementDefinition, type Position } from "cytoscape";
import fcose from "cytoscape-fcose";

import { communityOrder, communityStyle, themeColor } from "../palette";
import type { CentralityMetric, GraphResponse, RoleId } from "../types";
import { useCascas, type Casca } from "./cascas";
import { useRedimensionar } from "./useRedimensionar";
import { CLASSES_DA_SELECAO, destacarSelecao, enquadrarGrupo, estiloDaSelecao } from "./selecao";

cytoscape.use(fcose);

/** Acima disto, o navegador começa a engasgar e a figura deixa de comunicar. */
export const MAX_EDGES_CONFORTAVEL = 3000;

/**
 * Rótulos visíveis sem interação, conforme o zoom deixa ler
 * (`min-zoomed-font-size`). Acima destes limites, só no nó sob o mouse, no
 * selecionado e na vizinhança dele.
 *
 * Disciplinas têm nome que diz algo (`DDD_2014J`) e são poucas; alunos são
 * números de matrícula que, a partir de umas dezenas, só se sobrepõem.
 */
const MAX_DISCIPLINAS_ROTULADAS = 600;
const MAX_ALUNOS_ROTULADOS = 40;

/** Acima disto, o contorno das comunidades custa caro e deixa de dizer algo. */
const MAX_NOS_COM_BOLHAS = 300;

/** Vizinhos do nó selecionado com nome visível; acima disto, só o painel lista. */
/** Ao escolher um nó, a câmera não passa deste zoom, mesmo com poucos vizinhos. */
const ZOOM_MAX_SELECAO = 2.6;

/** Mesma pilha de fontes do CSS: o rótulo do canvas combina com a interface. */
const FONTE = '"Source Sans 3", system-ui, sans-serif';

/**
 * Tamanho do rótulo **na tela**, em px. O fit amplia grafos pequenos (7 nós
 * chegam a zoom 3), e um rótulo de 8–10px de modelo virava texto de 30px,
 * maior que qualquer título da interface. O tamanho de modelo passa a ser
 * `min(base, ROTULO_TELA / zoom)`: perto, o rótulo para em ~13px; longe, segue
 * a regra antiga (`min-zoomed-font-size` o esconde quando ilegível).
 */
const ROTULO_TELA = 13;

/** Até aqui as arestas são curvas (bézier); acima, retas curtas (haystack). */
const MAX_EDGES_CURVAS = 400;

/**
 * Limite do enquadramento editorial: grafos pequenos aproveitam a figura.
 * A folga considera o bounding box com rótulos; o usuário ainda pode
 * aproximar à mão (`maxZoom` do Cytoscape continua 4).
 */
const ZOOM_MAX_ENQUADRAMENTO = 3.6;

/**
 * Acima disto o desenho é "fixo": sem funções de
 * estilo que dependem do zoom. Cada atualização de estilo reavalia o grafo
 * inteiro (medido pelo revisor: ~5 ms em 81 nós, ~31 ms em 1250 nós/5000
 * arestas).
 */
const MAX_NOS_DINAMICO = 400;
const MAX_ARESTAS_DINAMICO = 1600;

/** O zoom é quantizado em 6 faixas por oitava (~12%): o estilo só reavalia ao trocar de faixa. */
const FAIXAS_POR_OITAVA = 6;

/** Controles de zoom: passo por clique e duração da animação (nenhuma com movimento reduzido). */
const PASSO_ZOOM = 1.25;
const DURACAO_ZOOM_MS = 200;

const PADDING_FIT = 36;
const PADDING_FIT_ESTREITO = 28;
const TAMANHO_MIN = 8;
const TAMANHO_MAX = 22;
const TAMANHO_NEUTRO = 14;
const DURACAO_MS = 150;

/**
 * Fator de escala dos nós pelo tamanho do grafo. Com 22 disciplinas os
 * nós podem ser grandes; com 1.870 alunos, no mesmo tamanho, viram uma
 * mancha. Raiz quadrada: a área ocupada cresce devagar com n.
 */
export function escala(n: number): number {
  return Math.min(1, Math.max(0.35, Math.sqrt(60 / Math.max(n, 1))));
}

/**
 * Posições por id de nó, compartilhadas entre montagens do componente.
 * É o que faz a troca de projeção preservar o lugar dos nós em comum:
 * o grafo novo parte de onde o anterior parou.
 */
const posicoes = new Map<string, Position>();

interface GraphViewProps {
  graph: GraphResponse;
  /** Nó → comunidade. `null` = cor pelo tipo do nó. */
  membership: Record<string, number> | null;
  /** Métrica que dimensiona os nós. `null` = todos do mesmo tamanho. */
  sizeBy: CentralityMetric | null;
  selected: string | null;
  /** Tema atual: o canvas relê os tokens CSS quando ele muda. */
  tema: "light" | "dark";
  onSelect: (nodeId: string | null) => void;
  /** Comunidade em foco (mouse na legenda): as outras esmaecem. */
  foco?: number | null;
  /** Só os nós com este papel ficam em destaque. */
  papel?: RoleId | null;
  papeis?: Record<string, { role: RoleId }> | null;
  /** Alunos em destaque (filtro de sinais); os demais ficam apagados. */
  realce?: ReadonlySet<string> | null;
  /** Nome por comunidade, escrito no contorno. */
  nomes?: Record<number, string>;
  /** Contorno translúcido em volta de cada comunidade. */
  bolhas?: boolean;
}

/** Tamanho de cada nó pela métrica, em escala linear entre o menor e o maior score. */
export function nodeSizes(
  graph: GraphResponse,
  sizeBy: CentralityMetric | null,
): Map<string, number> {
  const scores = sizeBy ? graph.centrality?.[sizeBy] : undefined;
  const sizes = new Map<string, number>();
  const f = escala(graph.nodes.length);
  if (!scores) {
    for (const node of graph.nodes) sizes.set(node.id, TAMANHO_NEUTRO * f);
    return sizes;
  }
  const values = graph.nodes.map((node) => scores[node.id] ?? 0);
  const min = Math.min(...values);
  const max = Math.max(...values);
  for (const node of graph.nodes) {
    const t = max > min ? ((scores[node.id] ?? 0) - min) / (max - min) : 0.5;
    sizes.set(node.id, f * (TAMANHO_MIN + t * (TAMANHO_MAX - TAMANHO_MIN)));
  }
  return sizes;
}

/** Posição inicial determinística (círculo por ordem de id) para quem ainda não tem posição. */
function posicaoInicial(ids: string[]): Map<string, Position> {
  const faltando = ids.filter((id) => !posicoes.has(id)).sort();
  const raio = Math.max(120, faltando.length * 4);
  const saida = new Map<string, Position>();
  faltando.forEach((id, i) => {
    const angulo = (2 * Math.PI * i) / Math.max(faltando.length, 1);
    saida.set(id, { x: raio * Math.cos(angulo), y: raio * Math.sin(angulo) });
  });
  return saida;
}

function toElements(graph: GraphResponse): ElementDefinition[] {
  const iniciais = posicaoInicial(graph.nodes.map((node) => node.id));
  const nodes: ElementDefinition[] = graph.nodes.map((node) => ({
    data: {
      id: node.id,
      label: node.label,
      kind: node.kind,
      size: TAMANHO_NEUTRO,
    },
    position: { ...(posicoes.get(node.id) ?? iniciais.get(node.id) ?? { x: 0, y: 0 }) },
  }));

  const edges: ElementDefinition[] = graph.edges.map((edge) => ({
    data: {
      id: `${edge.source}--${edge.target}`,
      source: edge.source,
      target: edge.target,
      weight: edge.weight,
    },
  }));

  return [...nodes, ...edges];
}

function ehDinamico(graph: GraphResponse): boolean {
  return graph.nodes.length <= MAX_NOS_DINAMICO && graph.edges.length <= MAX_ARESTAS_DINAMICO;
}

/** Faixa de zoom (índice inteiro) e o zoom representativo dela. */
function faixaDeZoom(zoom: number): number {
  return Math.round(Math.log2(Math.max(zoom, 0.01)) * FAIXAS_POR_OITAVA);
}
function zoomDaFaixa(faixa: number): number {
  return 2 ** (faixa / FAIXAS_POR_OITAVA);
}

/** Estilo editorial: preenchimento chapado, filetes e anel na forma do nó. */
function estilo(graph: GraphResponse, zoomReal: () => number): cytoscape.StylesheetJson {
  const zoom = ehDinamico(graph) ? zoomReal : () => 1;
  const px = (n: number) => () => n / Math.max(zoom(), 0.01);
  const pesos = graph.edges.map(e => e.weight);
  const minimo = pesos.length ? Math.min(...pesos) : 0;
  const maximo = pesos.length ? Math.max(...pesos) : 1;
  const relativo = (edge: cytoscape.EdgeSingular) => maximo > minimo ? (Number(edge.data("weight")) - minimo) / (maximo - minimo) : 0.5;
  const claro = document.documentElement.dataset.theme === "light";
  const cor = {
    student: themeColor("--node-student", "#56B4E9"),
    discipline: themeColor("--node-discipline", "#E69F00"),
    edge: themeColor("--edge", "#1A1915"),
    sheet: themeColor("--sheet", "#FFFFFF"),
    text: themeColor("--text", "#1A1915"),
    destaque: themeColor("--focus", "#1F5FBF"),
  };
  return [
    { selector: "node", style: {
      "background-color": cor.student, "background-opacity": 1,
      label: graph.nodes.length <= MAX_ALUNOS_ROTULADOS ? "data(label)" : "",
      "font-family": FONTE, "font-size": px(ROTULO_TELA), "font-weight": 600,
      "min-zoomed-font-size": 10, color: cor.text, "text-valign": "bottom",
      "text-margin-y": px(9), "text-outline-width": px(2),
      "text-outline-color": cor.sheet, "text-outline-opacity": 1,
      width: "data(size)", height: "data(size)",
      "border-width": px(claro ? 1.25 : 2),
      "border-color": claro ? cor.text : cor.sheet,
      "overlay-opacity": 0, "outline-color": cor.text,
      "outline-width": 0, "outline-offset": px(6),
      "transition-property": "width, height, opacity, background-color", "transition-duration": DURACAO_MS,
    } as unknown as cytoscape.Css.Node },
    { selector: 'node[kind = "discipline"]', style: {
      "background-color": cor.discipline, shape: "round-rectangle",
      label: graph.nodes.length <= MAX_DISCIPLINAS_ROTULADAS ? "data(label)" : "",
    } },
    { selector: "node.comunidade", style: {
      "background-color": "data(color)", shape: "data(shape)",
    } as unknown as cytoscape.Css.Node },
    { selector: "edge", style: {
      width: graph.edges.length <= MAX_EDGES_CURVAS * 4 ? (e: cytoscape.EdgeSingular) => (0.75 + relativo(e) * 4) / Math.max(zoom(), 0.01) : 0.5,
      "line-color": cor.edge, "line-cap": "round",
      "curve-style": graph.edges.length <= MAX_EDGES_CURVAS ? "bezier" : "haystack",
      opacity: (e: cytoscape.EdgeSingular) => 0.08 + relativo(e) * 0.22,
      "transition-property": "opacity", "transition-duration": DURACAO_MS,
    } as unknown as cytoscape.Css.Edge },
    { selector: ".apagado", style: { opacity: 0.06 } },
    { selector: "node.realce, node.rotulo", style: {
      label: "data(label)", "min-zoomed-font-size": 0, "text-opacity": 1,
      "font-size": px(ROTULO_TELA), "z-index": 10,
    } as unknown as cytoscape.Css.Node },
    { selector: "node.realce", style: { "outline-width": px(1), "outline-opacity": 0.5 } as unknown as cytoscape.Css.Node },
    { selector: "node.realce-papel", style: { "outline-width": px(2.5), "outline-opacity": 0.9, "z-index": 10 } as unknown as cytoscape.Css.Node },
    ...estiloDaSelecao({ destaque: cor.destaque, px, zoom, relativo, classeRotulo: "rotulo" }),
  ];
}

/** Folga do enquadramento: menor em tela estreita. */
function paddingDoFit(cy: Core): number {
  return cy.width() < 600 ? PADDING_FIT_ESTREITO : PADDING_FIT;
}

const movimentoReduzido = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Zoom em torno do centro do viewport, respeitando minZoom/maxZoom do Cytoscape. */
function zoomPorPasso(cy: Core, fator: number) {
  const nivel = Math.min(cy.maxZoom(), Math.max(cy.minZoom(), cy.zoom() * fator));
  const centro = { x: cy.width() / 2, y: cy.height() / 2 };
  cy.stop();
  if (movimentoReduzido()) cy.zoom({ level: nivel, renderedPosition: centro });
  else
    cy.animate(
      { zoom: { level: nivel, renderedPosition: centro } },
      { duration: DURACAO_ZOOM_MS, easing: "ease-out" },
    );
}

/**
 * Enquadra o grafo como no fim do layout: mesma folga, e o mesmo limite de
 * zoom (`ZOOM_MAX_ENQUADRAMENTO`) para que grafo pequeno não vire gigante.
 * Não mexe em posições, seleção nem dados.
 */
function enquadrar(cy: Core) {
  if (cy.elements().empty()) return;
  const padding = paddingDoFit(cy);
  const caixa = cy.elements().boundingBox();
  const livreX = Math.max(cy.width() - 2 * padding, 1);
  const livreY = Math.max(cy.height() - 2 * padding, 1);
  const nivel = Math.max(
    cy.minZoom(),
    Math.min(cy.maxZoom(), ZOOM_MAX_ENQUADRAMENTO, livreX / Math.max(caixa.w, 1), livreY / Math.max(caixa.h, 1)),
  );
  const pan = {
    x: cy.width() / 2 - nivel * (caixa.x1 + caixa.w / 2),
    y: cy.height() / 2 - nivel * (caixa.y1 + caixa.h / 2),
  };
  cy.stop();
  if (movimentoReduzido()) cy.viewport({ zoom: nivel, pan });
  else cy.animate({ zoom: nivel, pan }, { duration: DURACAO_ZOOM_MS, easing: "ease-out" });
}

/**
 * Roda o fcose, com duas redes de proteção.
 *
 * Com a maioria dos nós já posicionada, o layout continua de onde o grafo
 * anterior parou; sem isso, parte do zero. Nos dois casos a amostragem é
 * gulosa, não aleatória: mesma entrada, mesmo desenho.
 *
 * **Só continua em grafo conexo.** Com `randomize: false`, o fcose
 * quebra em grafo desconexo ("Cannot read properties of undefined
 * (reading 'nodeIndexes')", em `relocateComponent`) — o passo que
 * reposiciona as componentes depende do passo espectral, que só roda com
 * `randomize: true`. Se ainda assim o layout falhar, tenta do zero; se
 * falhar de novo, fica a grade: um desenho feio é melhor que uma tela em
 * branco na apresentação.
 */
function rodarLayout(cy: Core, { continuar, pesado }: { continuar: boolean; pesado: boolean }) {
  const padding = paddingDoFit(cy);
  const base = {
    name: "fcose",
    samplingType: false,
    quality: pesado ? "draft" : "default",
    animate: !pesado,
    animationDuration: 700,
    nodeRepulsion: 6000,
    idealEdgeLength: 60,
    fit: true,
    // Folga do layout preservada; números e painel ocupam áreas próprias.
    padding,
  };
  const conexo = cy.elements().components().length <= 1;
  const tentativas = [
    { ...base, randomize: !(continuar && conexo) },
    { ...base, randomize: true, packComponents: true },
    { name: "grid", fit: true, padding },
  ];
  for (const opcoes of tentativas) {
    try {
      cy.layout(opcoes as cytoscape.LayoutOptions).run();
      return;
    } catch (erro) {
      console.warn(`[GraphView] layout ${opcoes.name} falhou, tentando o próximo`, erro);
    }
  }
}

/** O que o pai pode pedir ao grafo (controles de zoom do palco). */
export interface GraphViewHandle {
  aproximar: () => void;
  afastar: () => void;
  centralizar: () => void;
}

export const GraphView = forwardRef<GraphViewHandle, GraphViewProps>(function GraphView(
  { graph, membership, sizeBy, selected, tema, onSelect, foco = null, papel = null, papeis = null, realce = null, nomes, bolhas = false },
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [cy, setCy] = useState<Core | null>(null);
  // O callback mais recente sem recriar o Cytoscape quando o pai re-renderiza.
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  useImperativeHandle(
    ref,
    () => ({
      aproximar: () => cyRef.current && zoomPorPasso(cyRef.current, PASSO_ZOOM),
      afastar: () => cyRef.current && zoomPorPasso(cyRef.current, 1 / PASSO_ZOOM),
      centralizar: () => cyRef.current && enquadrar(cyRef.current),
    }),
    [],
  );

  useRedimensionar(containerRef, cyRef, enquadrar);

  // 1. Um Cytoscape por grafo.
  useEffect(() => {
    if (!containerRef.current) return;

    const pesado = graph.edges.length > MAX_EDGES_CONFORTAVEL;
    const conhecidos = graph.nodes.filter((node) => posicoes.has(node.id)).length;
    const continuar = conhecidos >= graph.nodes.length / 2;

    const cy = cytoscape({
      container: containerRef.current,
      elements: toElements(graph),
      style: estilo(graph, () => zoomDaFaixa(faixaDeZoom(cyRef.current?.zoom() ?? 1))),
      layout: { name: "preset" },
      wheelSensitivity: 0.2,
      minZoom: 0.05,
      maxZoom: 4,
    });

    cy.on("layoutstop", () => {
      // Mesma câmera do botão Centralizar, sem alterar as posições do fcose.
      enquadrar(cy);
      cy.nodes().forEach((node) => {
        posicoes.set(node.id(), { ...node.position() });
      });
    });
    rodarLayout(cy, { continuar, pesado });

    // Rótulo, anel e arestas dependem do zoom. O estilo só é reavaliado ao
    // cruzar uma faixa de zoom (~12%), no máximo uma vez por quadro — e nunca
    // em grafo grande, onde o estilo é fixo.
    let quadro = 0;
    let ultimaFaixa = Number.NaN;
    const aoMudarZoom = () => {
      if (quadro) return;
      quadro = requestAnimationFrame(() => {
        quadro = 0;
        if (cy.destroyed()) return;
        const faixa = faixaDeZoom(cy.zoom());
        if (faixa === ultimaFaixa) return;
        ultimaFaixa = faixa;
        cy.style().update();
      });
    };
    if (ehDinamico(graph)) cy.on("zoom", aoMudarZoom);

    cy.on("mouseover", "node", (event) => {
      event.target.addClass("realce");
      if (containerRef.current) containerRef.current.style.cursor = "pointer";
    });
    cy.on("mouseout", "node", (event) => {
      event.target.removeClass("realce");
      if (containerRef.current) containerRef.current.style.cursor = "";
    });
    cy.on("tap", "node", (event) => onSelectRef.current(event.target.id()));
    cy.on("tap", (event) => {
      if (event.target === cy) onSelectRef.current(null);
    });

    cyRef.current = cy;
    setCy(cy);
    return () => {
      cy.off("zoom", aoMudarZoom);
      if (quadro) cancelAnimationFrame(quadro);
      cy.nodes().forEach((node) => {
        posicoes.set(node.id(), { ...node.position() });
      });
      cy.destroy();
      cyRef.current = null;
      setCy(null);
    };
  }, [graph]);

  // 2. Cor e forma pela partição — sem recriar o grafo.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    const ordem = membership ? communityOrder(membership) : null;
    cy.batch(() => {
      cy.nodes().forEach((node) => {
        const comunidade = membership?.[node.id()];
        if (ordem && comunidade !== undefined) {
          const { color, shape } = communityStyle(ordem.get(comunidade) ?? 0);
          node.data({ color, shape });
          node.addClass("comunidade");
        } else {
          node.removeClass("comunidade");
        }
      });

    });
  }, [graph, membership, tema]);

  // Troca de tema: refaz a folha de estilo com as cores dos tokens, sem tocar
  // em dados, posições nem seleção. A primeira montagem já nasce no tema atual.
  const temaAplicado = useRef(tema);
  useEffect(() => {
    if (temaAplicado.current === tema) return;
    temaAplicado.current = tema;
    const cy = cyRef.current;
    if (!cy) return;
    cy.style(estilo(graph, () => zoomDaFaixa(faixaDeZoom(cy.zoom()))));
  }, [graph, tema]);

  // 3. Tamanho pela métrica, animado pela transição de estilo.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    const tamanhos = nodeSizes(graph, sizeBy);
    cy.batch(() => {
      cy.nodes().forEach((node) => {
        node.data("size", tamanhos.get(node.id()) ?? TAMANHO_NEUTRO);
      });
    });
  }, [graph, sizeBy]);

  // 4. Seleção vinda de fora (painel), foco por comunidade, filtro de papel
  // e destaque da vizinhança. Só classes: nada é refeito.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.batch(() => {
      cy.elements().removeClass(`apagado rotulo realce-papel ${CLASSES_DA_SELECAO}`);
      cy.nodes(":selected").unselect();
      if (!selected && foco !== null && membership) {
        const membros = (id: string) => membership[id] === foco;
        cy.nodes().forEach((n) => {
          if (!membros(n.id())) n.addClass("apagado");
        });
        cy.edges().forEach((e) => {
          if (!(membros(e.source().id()) && membros(e.target().id()))) e.addClass("apagado");
        });
      }
      if (!selected && papel && papeis) {
        cy.nodes().forEach((n) => {
          if (papeis[n.id()]?.role === papel) n.addClass("realce-papel");
          else n.addClass("apagado");
        });
        cy.edges().addClass("apagado");
      }
      if (!selected && realce) {
        cy.nodes().forEach((n) => {
          if (realce.has(n.id())) n.addClass("realce-papel");
          else n.addClass("apagado");
        });
        cy.edges().addClass("apagado");
      }
      // Só os vizinhos de ligação mais forte mostram o nome: com dezenas, os
      // rótulos se sobrepõem, e a lista completa está no painel do nó.
      if (selected) destacarSelecao(cy, selected, "rotulo");
    });
  }, [graph, selected, foco, papel, papeis, realce, membership]);

  // 4b. A câmera acompanha a seleção: enquadra o nó com os vizinhos e, ao
  // soltar, volta ao grafo inteiro. Só reage a mudar de seleção.
  const selecionadoAntes = useRef<string | null>(null);
  useEffect(() => {
    const cy = cyRef.current;
    const antes = selecionadoAntes.current;
    selecionadoAntes.current = selected;
    if (!cy) return;
    if (selected) {
      const alvo = cy.getElementById(selected);
      if (alvo.nonempty()) enquadrarGrupo(cy, alvo.closedNeighborhood().nodes(), ZOOM_MAX_SELECAO, DURACAO_ZOOM_MS * 2);
    } else if (antes) {
      enquadrar(cy);
    }
  }, [selected]);

  // 5. Contornos das comunidades, só em grafo pequeno.
  const cascas = useMemo<Casca[]>(() => {
    if (!bolhas || !membership || graph.nodes.length > MAX_NOS_COM_BOLHAS) return [];
    const ordem = communityOrder(membership);
    const grupos = new Map<number, string[]>();
    for (const [no, comunidade] of Object.entries(membership)) {
      const lista = grupos.get(comunidade) ?? [];
      lista.push(no);
      grupos.set(comunidade, lista);
    }
    return [...grupos]
      .filter(([, ids]) => ids.length >= 2)
      .map(([comunidade, ids]) => ({
        ids,
        cor: communityStyle(ordem.get(comunidade) ?? 0).color,
        rotulo: nomes?.[comunidade],
      }));
  }, [bolhas, membership, graph, nomes]);
  useCascas(cy, cascas, tema);

  const pesado = graph.edges.length > MAX_EDGES_CONFORTAVEL;
  const { truncation } = graph;

  return (
    <div className="graph-view">
      {(pesado || truncation.truncated) && (
        <p className="aviso" role="status">
          {truncation.truncated && (
            <>
              {truncation.criterion === "backbone" && (truncation.k_per_node ?? 0) > 0
                ? `Esqueleto: as ${truncation.k_per_node} ligações mais fortes de cada nó`
                : truncation.criterion === "backbone"
                  ? "Nem uma ligação por nó coube no limite: ficaram as mais fortes, e alguns nós aparecem soltos"
                  : "As arestas de maior peso"}{" "}
              — {truncation.n_edges_returned.toLocaleString("pt-BR")} de{" "}
              {truncation.n_edges_total.toLocaleString("pt-BR")} arestas; todos os{" "}
              {truncation.n_nodes.toLocaleString("pt-BR")} nós estão aqui.{" "}
            </>
          )}
          {pesado && (
            <>
              Acima de {MAX_EDGES_CONFORTAVEL.toLocaleString("pt-BR")} arestas o desenho é
              simplificado e fica mais lento.
            </>
          )}
        </p>
      )}
      <div
        ref={containerRef}
        className="graph-canvas"
        tabIndex={0}
        role="group"
        aria-label="Grafo interativo. Com o foco aqui: + aproxima, − afasta e 0 centraliza."
      />
    </div>
  );
});
