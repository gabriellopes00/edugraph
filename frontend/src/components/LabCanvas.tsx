/**
 * Grafo do laboratório — ADR-0013.
 *
 * Um único Cytoscape guarda os dois grafos: o **bipartido** (alunos de um
 * lado, disciplinas do outro, em duas colunas) e a **projeção** (só um
 * tipo de nó, posicionado por força). Cada quadro da animação
 * (`lab/frames.ts`) diz o que aparece; este componente só liga e desliga
 * classes e anima a mudança de lugar dos nós — por isso o controle
 * deslizante anda para os dois lados.
 *
 * Os contornos das comunidades (`cascas.ts`) crescem junto com os grupos:
 * é a forma mais direta de ver o Louvain juntando alunos.
 */

import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from "react";
import cytoscape, { type Core, type ElementDefinition, type Position } from "cytoscape";
import fcose from "cytoscape-fcose";

import { communityStyle, themeColor } from "../palette";
import { indicesDeCor, type Estado } from "../lab/frames";
import type { CentralityMetric, LabRun, RoleId } from "../types";
import { useCascas, type Casca } from "./cascas";
import { CLASSES_DA_SELECAO, destacarSelecao, enquadrarGrupo, estiloDaSelecao } from "./selecao";

cytoscape.use(fcose);

const FONTE = '"Source Sans 3", system-ui, sans-serif';
const TAMANHO_ALUNO = 15;
const TAMANHO_MIN = 9;
const TAMANHO_MAX = 26;
const ZOOM_MAXIMO_DO_ENQUADRAMENTO = 2.4;
/** Ao escolher um aluno, a câmera não passa deste zoom, mesmo com poucos vizinhos. */
const ZOOM_MAXIMO_DA_SELECAO = 2.2;
/** Acima disto, o nome do aluno não cabe no grafo e só aparece sob o mouse. */
const MAX_ALUNOS_ROTULADOS = 60;
const DURACAO_MOVIMENTO_MS = 700;

const movimentoReduzido = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export interface LabCanvasHandle {
  aproximar: () => void;
  afastar: () => void;
  centralizar: () => void;
}

interface LabCanvasProps {
  run: LabRun;
  estado: Estado;
  metrica: CentralityMetric | null;
  tema: "light" | "dark";
  selected: string | null;
  onSelect: (id: string | null) => void;
  /** Comunidade em foco (passar o mouse na legenda): as outras esmaecem. */
  foco: number | null;
  /** Só este papel fica em destaque. */
  papel: RoleId | null;
  /** Bolhas em volta das comunidades. */
  bolhas: boolean;
  /** Contorno tracejado das áreas plantadas (a "resposta certa"). */
  plantadas: boolean;
  nomes: Record<number, string>;
  papeis: Record<string, { role: RoleId }>;
  /** Alunos em destaque (filtro de sinais); os demais ficam apagados. */
  realce: ReadonlySet<string> | null;
}

/** Tudo o que se calcula uma vez por rodada. */
interface Montagem {
  colunas: Map<string, Position>;
  projecao: Map<string, Position>;
  mantidos: Set<string>;
  idsBip: string[];
  idsProj: string[];
  /** Índice, em `removed`, → id da aresta da projeção. */
  idsRemovidas: string[];
}

const comparar = (a: string, b: string) => a.localeCompare(b, "pt-BR");

function posicoesDasColunas(run: LabRun): Map<string, Position> {
  const alunos = [...run.bipartite.students].sort((a, b) => comparar(a.label, b.label));
  const disciplinas = [...run.bipartite.disciplines].sort((a, b) => comparar(a.label, b.label));
  const altura = Math.max(360, alunos.length * 15);
  const saida = new Map<string, Position>();
  alunos.forEach((a, i) => {
    saida.set(a.id, { x: 0, y: alunos.length > 1 ? (i * altura) / (alunos.length - 1) : altura / 2 });
  });
  const passo = Math.min(70, altura / Math.max(disciplinas.length, 1));
  disciplinas.forEach((d, i) => {
    saida.set(d.id, { x: 600, y: altura / 2 + (i - (disciplinas.length - 1) / 2) * passo });
  });
  return saida;
}

/** Posição da projeção por força, calculada à parte para não mexer no grafo visível. */
function posicoesDaProjecao(run: LabRun): Map<string, Position> {
  const pesos = run.projection.edges.map((e) => e.weight);
  const minimo = Math.min(...pesos);
  const maximo = Math.max(...pesos);
  const relativo = (peso: number) => (maximo > minimo ? (peso - minimo) / (maximo - minimo) : 0.5);
  const elementos: ElementDefinition[] = [
    ...run.projection.nodes.map((n) => ({ data: { id: n.id } })),
    ...run.projection.edges.map((e, i) => ({
      data: { id: `e${i}`, source: e.source, target: e.target, weight: e.weight },
    })),
  ];
  // Quanto mais nós, mais espaço entre eles: os nomes precisam caber.
  const espaco = 1 + run.projection.nodes.length / 28;
  const oculto = cytoscape({ headless: true, styleEnabled: false, elements: elementos });
  try {
    oculto
      .layout({
        name: "fcose",
        animate: false,
        randomize: true,
        packComponents: true,
        quality: "default",
        nodeRepulsion: () => 22000 * espaco,
        idealEdgeLength: (edge: cytoscape.EdgeSingular) =>
          (130 - 90 * relativo(Number(edge.data("weight")))) * espaco,
      } as cytoscape.LayoutOptions)
      .run();
  } catch {
    oculto.layout({ name: "circle", animate: false } as cytoscape.LayoutOptions).run();
  }
  const saida = new Map<string, Position>();
  oculto.nodes().forEach((n) => {
    saida.set(n.id(), { ...n.position() });
  });
  oculto.destroy();
  return saida;
}

function elementos(run: LabRun, colunas: Map<string, Position>): {
  lista: ElementDefinition[];
  idsBip: string[];
  idsProj: string[];
  idsRemovidas: string[];
} {
  const ordemAluno = new Map(
    [...run.bipartite.students].sort((a, b) => comparar(a.label, b.label)).map((s, i) => [s.id, i]),
  );
  const lista: ElementDefinition[] = [];
  for (const s of run.bipartite.students) {
    lista.push({
      data: { id: s.id, label: s.label, kind: "student", size: TAMANHO_ALUNO },
      position: { ...colunas.get(s.id)! },
    });
  }
  for (const d of run.bipartite.disciplines) {
    lista.push({
      data: { id: d.id, label: d.label, kind: "discipline", size: TAMANHO_ALUNO + 4 },
      position: { ...colunas.get(d.id)! },
    });
  }

  const bip = [...run.bipartite.edges].sort(
    (a, b) => (ordemAluno.get(a[0]) ?? 0) - (ordemAluno.get(b[0]) ?? 0) || comparar(a[1], b[1]),
  );
  const idsBip = bip.map((e, i) => {
    const id = `b${i}`;
    lista.push({ data: { id, source: e[0], target: e[1], weight: e[2] }, classes: "bip oculto" });
    return id;
  });

  const proj = run.projection.edges
    .map((e, i) => ({ e, i }))
    .sort((a, b) => b.e.weight - a.e.weight || a.i - b.i);
  const idDaProjecao = new Map<string, string>();
  const idsProj = proj.map(({ e }, ordem) => {
    const id = `p${ordem}`;
    lista.push({
      data: { id, source: e.source, target: e.target, weight: e.weight },
      classes: "proj oculto",
    });
    idDaProjecao.set(`${e.source}\u0000${e.target}`, id);
    idDaProjecao.set(`${e.target}\u0000${e.source}`, id);
    return id;
  });

  const gn = run.girvan_newman;
  const idsRemovidas = gn
    ? gn.removed.map(([i, j]) => idDaProjecao.get(`${gn.nodes[i]}\u0000${gn.nodes[j]}`) ?? "")
    : [];
  return { lista, idsBip, idsProj, idsRemovidas };
}

function estilo(cy: () => Core | null, tema: string, run: LabRun): cytoscape.StylesheetJson {
  const claro = tema === "light";
  const cor = {
    aluno: themeColor("--node-student", "#56B4E9"),
    disciplina: themeColor("--node-discipline", "#E69F00"),
    aresta: themeColor("--edge", "#1A1915"),
    folha: themeColor("--sheet", "#FFFFFF"),
    texto: themeColor("--text", "#1A1915"),
    destaque: themeColor("--focus", "#1F5FBF"),
    neutro: claro ? "#bdb8ac" : "#6e6a60",
  };
  const zoom = () => Math.max(cy()?.zoom() ?? 1, 0.01);
  const px = (n: number) => () => n / zoom();
  const pesos = run.projection.edges.map((e) => e.weight);
  const minimo = Math.min(...pesos, 0);
  const maximo = Math.max(...pesos, 1);
  const relativo = (e: cytoscape.EdgeSingular) =>
    maximo > minimo ? (Number(e.data("weight")) - minimo) / (maximo - minimo) : 0.5;
  // Em tela estreita os nomes dos alunos se sobrepõem: só aparecem ao tocar ou passar o mouse.
  const larga = (cy()?.width() ?? 1000) >= 560;
  const rotulado =
    (run.bipartite.students.length <= MAX_ALUNOS_ROTULADOS && larga) ||
    run.projection.side === "discipline";

  return [
    {
      selector: "node",
      style: {
        "background-color": cor.neutro,
        width: "data(size)",
        height: "data(size)",
        label: rotulado ? "data(label)" : "",
        "font-family": FONTE,
        "font-size": px(11.5),
        "font-weight": 600,
        color: cor.texto,
        "text-valign": "bottom",
        "text-margin-y": px(8),
        "text-outline-width": px(2),
        "text-outline-color": cor.folha,
        "text-outline-opacity": 1,
        "min-zoomed-font-size": 6,
        "border-width": px(claro ? 1.1 : 1.8),
        "border-color": claro ? cor.texto : cor.folha,
        "overlay-opacity": 0,
        "outline-color": cor.texto,
        "outline-width": 0,
        "outline-offset": px(5),
        "transition-property": "background-color, width, height, opacity, outline-width",
        "transition-duration": 260,
      } as unknown as cytoscape.Css.Node,
    },
    {
      selector: 'node[kind = "student"]',
      style: { "background-color": cor.aluno } as unknown as cytoscape.Css.Node,
    },
    {
      selector: 'node[kind = "discipline"]',
      style: {
        "background-color": cor.disciplina,
        shape: "round-rectangle",
        label: "data(label)",
      } as unknown as cytoscape.Css.Node,
    },
    {
      selector: "node.neutro",
      style: { "background-color": cor.neutro } as unknown as cytoscape.Css.Node,
    },
    {
      selector: "node.comunidade",
      style: { "background-color": "data(color)", shape: "data(shape)" } as unknown as cytoscape.Css.Node,
    },
    {
      selector: "node.col-esq",
      style: {
        "text-halign": "left",
        "text-valign": "center",
        "text-margin-x": px(-9),
        "text-margin-y": 0,
      } as unknown as cytoscape.Css.Node,
    },
    {
      selector: "node.col-dir",
      style: {
        "text-halign": "right",
        "text-valign": "center",
        "text-margin-x": px(9),
        "text-margin-y": 0,
      } as unknown as cytoscape.Css.Node,
    },
    {
      selector: "node.oculto",
      style: { opacity: 0, events: "no", "text-opacity": 0 } as unknown as cytoscape.Css.Node,
    },
    {
      selector: "edge",
      style: {
        "line-color": cor.aresta,
        "curve-style": "haystack",
        "haystack-radius": 0,
        "line-cap": "round",
        "overlay-opacity": 0,
      } as unknown as cytoscape.Css.Edge,
    },
    {
      selector: "edge.bip",
      style: { width: px(1.1), opacity: 0.34 } as unknown as cytoscape.Css.Edge,
    },
    {
      selector: "edge.proj",
      style: {
        width: (e: cytoscape.EdgeSingular) => (0.7 + relativo(e) * 3.6) / zoom(),
        opacity: (e: cytoscape.EdgeSingular) => 0.1 + relativo(e) * 0.26,
      } as unknown as cytoscape.Css.Edge,
    },
    {
      selector: "edge.intra",
      style: {
        "line-color": "data(color)",
        opacity: (e: cytoscape.EdgeSingular) => 0.3 + relativo(e) * 0.4,
      } as unknown as cytoscape.Css.Edge,
    },
    {
      selector: "edge.piscando",
      style: {
        "line-color": "#D55E00",
        width: px(3),
        opacity: 0.95,
        "z-index": 30,
      } as unknown as cytoscape.Css.Edge,
    },
    {
      selector: "edge.oculto",
      style: { display: "none" } as unknown as cytoscape.Css.Edge,
    },
    { selector: ".apagado", style: { opacity: 0.07 } },
    // As disciplinas e as matrículas somem na projeção, mas continuam no grafo: esmaecer não pode trazê-las de volta.
    {
      selector: "node.oculto",
      style: { opacity: 0, events: "no", "text-opacity": 0 } as unknown as cytoscape.Css.Node,
    },
    {
      selector: "node.realce, node:selected, node.vizinho-rotulo",
      style: {
        label: "data(label)",
        "min-zoomed-font-size": 0,
        "z-index": 10,
      } as unknown as cytoscape.Css.Node,
    },
    {
      selector: "node.realce-papel",
      style: {
        "outline-width": px(2.5),
        "outline-opacity": 0.9,
      } as unknown as cytoscape.Css.Node,
    },
    ...estiloDaSelecao({
      destaque: cor.destaque,
      px,
      zoom,
      relativo,
      classeRotulo: "vizinho-rotulo",
    }),
  ];
}

export const LabCanvas = forwardRef<LabCanvasHandle, LabCanvasProps>(function LabCanvas(
  { run, estado, metrica, tema, selected, onSelect, foco, papel, bolhas, plantadas, nomes, papeis, realce },
  ref,
) {
  const hostRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const montagemRef = useRef<Montagem | null>(null);
  const posicaoRef = useRef<"colunas" | "projecao" | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const [cy, setCy] = useState<Core | null>(null);

  useImperativeHandle(
    ref,
    () => ({
      aproximar: () => cyRef.current?.zoom({ level: cyRef.current.zoom() * 1.25, renderedPosition: centro(cyRef.current) }),
      afastar: () => cyRef.current?.zoom({ level: cyRef.current.zoom() / 1.25, renderedPosition: centro(cyRef.current) }),
      centralizar: () => cyRef.current && enquadrar(cyRef.current, false),
    }),
    [],
  );

  // 1. Um Cytoscape por rodada.
  useEffect(() => {
    if (!hostRef.current) return;
    const colunas = posicoesDasColunas(run);
    const projecao = posicoesDaProjecao(run);
    const { lista, idsBip, idsProj, idsRemovidas } = elementos(run, colunas);
    const instancia = cytoscape({
      container: hostRef.current,
      elements: lista,
      style: [],
      layout: { name: "preset" },
      wheelSensitivity: 0.2,
      minZoom: 0.1,
      maxZoom: 5,
    });
    instancia.style(estilo(() => instancia, tema, run));
    montagemRef.current = {
      colunas,
      projecao,
      mantidos: new Set(run.projection.nodes.map((n) => n.id)),
      idsBip,
      idsProj,
      idsRemovidas,
    };
    posicaoRef.current = null;

    let quadro = 0;
    instancia.on("zoom", () => {
      if (quadro) return;
      quadro = requestAnimationFrame(() => {
        quadro = 0;
        if (!instancia.destroyed()) instancia.style().update();
      });
    });
    instancia.on("mouseover", "node", (e) => e.target.addClass("realce"));
    instancia.on("mouseout", "node", (e) => e.target.removeClass("realce"));
    instancia.on("tap", "node", (e) => onSelectRef.current(e.target.id()));
    instancia.on("tap", (e) => {
      if (e.target === instancia) onSelectRef.current(null);
    });

    cyRef.current = instancia;
    setCy(instancia);
    return () => {
      if (quadro) cancelAnimationFrame(quadro);
      instancia.destroy();
      cyRef.current = null;
      setCy(null);
    };
    // O tema é lido ao montar; a troca é tratada no efeito seguinte.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run]);

  useEffect(() => {
    const instancia = cyRef.current;
    if (instancia) instancia.style(estilo(() => instancia, tema, run));
  }, [tema, run]);

  // 2. O estado do quadro: o que aparece, onde está e de que cor.
  useEffect(() => {
    const instancia = cyRef.current;
    const m = montagemRef.current;
    if (!instancia || !m) return;
    aplicar(instancia, m, run, estado, metrica, posicaoRef);
  }, [cy, run, estado, metrica]);

  // 3. Foco, papel e seleção: só classes, sem refazer nada.
  useEffect(() => {
    const instancia = cyRef.current;
    if (!instancia) return;
    const resultado = estado.etapa === "resultado";
    instancia.batch(() => {
      instancia.elements().removeClass(`apagado realce-papel vizinho-rotulo ${CLASSES_DA_SELECAO}`);
      instancia.nodes(":selected").unselect();
      if (resultado && foco !== null) {
        const membros = (id: string) => run.result.membership[id] === foco;
        instancia.nodes().forEach((n) => {
          if (!membros(n.id())) n.addClass("apagado");
        });
        instancia.edges().forEach((e) => {
          if (!(membros(e.source().id()) && membros(e.target().id()))) e.addClass("apagado");
        });
      }
      if (resultado && papel) {
        instancia.nodes().forEach((n) => {
          if (papeis[n.id()]?.role === papel) n.addClass("realce-papel");
          else n.addClass("apagado");
        });
        instancia.edges().addClass("apagado");
      }
      if (resultado && realce) {
        instancia.nodes().forEach((n) => {
          if (realce.has(n.id())) n.addClass("realce-papel");
          else n.addClass("apagado");
        });
        instancia.edges().addClass("apagado");
      }
      if (selected) destacarSelecao(instancia, selected, "vizinho-rotulo");
    });
  }, [cy, run, estado.etapa, foco, papel, selected, papeis, realce]);

  // 3b. A câmera acompanha a seleção: enquadra o aluno com os vizinhos e,
  // ao soltar, volta ao grafo inteiro. Só reage a mudar de seleção.
  const selecionadoAntes = useRef<string | null>(null);
  useEffect(() => {
    const instancia = cyRef.current;
    const antes = selecionadoAntes.current;
    selecionadoAntes.current = selected;
    if (!instancia) return;
    if (selected) {
      const alvo = instancia.getElementById(selected);
      if (alvo.empty()) return;
      const visiveis = alvo.connectedEdges().not(".oculto");
      enquadrarGrupo(instancia, alvo.union(visiveis.connectedNodes()), ZOOM_MAXIMO_DA_SELECAO);
    } else if (antes) {
      enquadrar(instancia, true);
    }
  }, [cy, selected]);

  // Bolhas das comunidades (e das áreas plantadas, na revelação).
  const cascas = useMemo<Casca[]>(() => {
    const saida: Casca[] = [];
    const etapa = estado.etapa;
    if (bolhas && estado.grupos && (etapa === "algoritmo" || etapa === "resultado")) {
      const indices = indicesDeCor(estado.grupos, run.result.membership, etapa === "resultado");
      const porGrupo = new Map<number, string[]>();
      for (const [no, g] of Object.entries(estado.grupos)) {
        const lista = porGrupo.get(g) ?? [];
        lista.push(no);
        porGrupo.set(g, lista);
      }
      for (const [grupo, ids] of porGrupo) {
        const indice = indices[ids[0]];
        if (indice == null || ids.length < 2) continue;
        saida.push({
          ids,
          cor: communityStyle(indice).color,
          rotulo: etapa === "resultado" ? nomes[grupo] : undefined,
        });
      }
    }
    const verdade = run.reveal.planted;
    if (plantadas && verdade && etapa === "resultado") {
      const porArea = new Map<string, string[]>();
      for (const [no, area] of Object.entries(verdade.node_area)) {
        const lista = porArea.get(area) ?? [];
        lista.push(no);
        porArea.set(area, lista);
      }
      for (const [area, ids] of porArea) {
        saida.push({
          ids,
          cor: "#6e6a60",
          rotulo: `área plantada: ${area}`,
          tracejada: true,
          rotuloEmbaixo: true,
        });
      }
    }
    return saida;
  }, [bolhas, plantadas, estado.grupos, estado.etapa, run, nomes]);
  useCascas(cy, cascas, tema);

  return (
    <div className="graph-view">
      <div
        ref={hostRef}
        className="graph-canvas"
        tabIndex={0}
        role="group"
        aria-label="Grafo do laboratório. Com o foco aqui: + aproxima, − afasta e 0 centraliza."
      />
    </div>
  );
});

const centro = (instancia: Core) => ({ x: instancia.width() / 2, y: instancia.height() / 2 });

function enquadrar(instancia: Core, animar: boolean) {
  const visiveis = instancia.elements().not(".oculto");
  if (visiveis.empty()) return;
  const padding = instancia.width() < 600 ? 28 : 56;
  const caixa = visiveis.boundingBox({});
  const nivel = Math.max(
    instancia.minZoom(),
    Math.min(
      ZOOM_MAXIMO_DO_ENQUADRAMENTO,
      (instancia.width() - 2 * padding) / Math.max(caixa.w, 1),
      (instancia.height() - 2 * padding) / Math.max(caixa.h, 1),
    ),
  );
  const pan = {
    x: instancia.width() / 2 - nivel * (caixa.x1 + caixa.w / 2),
    y: instancia.height() / 2 - nivel * (caixa.y1 + caixa.h / 2),
  };
  instancia.stop();
  if (animar && !movimentoReduzido()) {
    instancia.animate({ zoom: nivel, pan }, { duration: DURACAO_MOVIMENTO_MS, easing: "ease-in-out" });
  } else {
    instancia.viewport({ zoom: nivel, pan });
  }
}

/**
 * Enquadra um conjunto de posições **de destino**, não as de agora: durante a
 * troca de grafo os nós ainda estão em trânsito, e o enquadramento pela caixa
 * deles sairia pequeno e fora do centro.
 */
function vistaPara(instancia: Core, pontos: Position[], margem: { x: number; y: number }, animar: boolean) {
  if (pontos.length === 0) return;
  const xs = pontos.map((p) => p.x);
  const ys = pontos.map((p) => p.y);
  const x1 = Math.min(...xs);
  const x2 = Math.max(...xs);
  const y1 = Math.min(...ys);
  const y2 = Math.max(...ys);
  const nivel = Math.max(
    instancia.minZoom(),
    Math.min(
      ZOOM_MAXIMO_DO_ENQUADRAMENTO,
      (instancia.width() - 2 * margem.x) / Math.max(x2 - x1, 1),
      (instancia.height() - 2 * margem.y) / Math.max(y2 - y1, 1),
    ),
  );
  const pan = {
    x: instancia.width() / 2 - nivel * ((x1 + x2) / 2),
    y: instancia.height() / 2 - nivel * ((y1 + y2) / 2),
  };
  instancia.stop(true);
  if (animar) instancia.animate({ zoom: nivel, pan }, { duration: DURACAO_MOVIMENTO_MS, easing: "ease-in-out" });
  else instancia.viewport({ zoom: nivel, pan });
}

/** Tamanho de cada nó pela métrica, entre o menor e o maior score. */
function tamanhos(run: LabRun, metrica: CentralityMetric | null): Map<string, number> {
  const saida = new Map<string, number>();
  const pontos = metrica ? run.centrality[metrica] : undefined;
  const fator = Math.min(1, Math.max(0.55, Math.sqrt(40 / Math.max(run.projection.nodes.length, 1))));
  if (!pontos) {
    for (const n of run.projection.nodes) saida.set(n.id, TAMANHO_ALUNO * fator + 2);
    return saida;
  }
  const valores = run.projection.nodes.map((n) => pontos[n.id] ?? 0);
  const minimo = Math.min(...valores);
  const maximo = Math.max(...valores);
  for (const n of run.projection.nodes) {
    const t = maximo > minimo ? ((pontos[n.id] ?? 0) - minimo) / (maximo - minimo) : 0.5;
    saida.set(n.id, fator * (TAMANHO_MIN + t * (TAMANHO_MAX - TAMANHO_MIN)));
  }
  return saida;
}

function aplicar(
  instancia: Core,
  m: Montagem,
  run: LabRun,
  estado: Estado,
  metrica: CentralityMetric | null,
  posicaoRef: { current: "colunas" | "projecao" | null },
) {
  const etapa = estado.etapa;
  const naProjecao = etapa !== "matriculas";
  const alvo = naProjecao ? "projecao" : "colunas";
  const posicoes = naProjecao ? m.projecao : m.colunas;
  const indices = estado.grupos
    ? indicesDeCor(estado.grupos, run.result.membership, etapa === "resultado")
    : null;
  const tamanho = etapa === "resultado" ? tamanhos(run, metrica) : null;

  instancia.batch(() => {
    instancia.nodes().forEach((n) => {
      const id = n.id();
      const mantido = m.mantidos.has(id);
      n.toggleClass("oculto", naProjecao && !mantido);
      n.toggleClass("col-esq", !naProjecao && n.data("kind") === "student");
      n.toggleClass("col-dir", !naProjecao && n.data("kind") === "discipline");
      const indice = naProjecao && mantido ? indices?.[id] : null;
      if (indice != null) {
        const { color, shape } = communityStyle(indice);
        n.data({ color, shape });
        n.addClass("comunidade");
      } else {
        n.removeClass("comunidade");
      }
      n.data("size", tamanho?.get(id) ?? (n.data("kind") === "student" ? TAMANHO_ALUNO : TAMANHO_ALUNO + 4));
    });

    m.idsBip.forEach((id, i) => {
      instancia.getElementById(id).toggleClass("oculto", !(etapa === "matriculas" && i < estado.matriculas));
    });

    const removidas = new Set(m.idsRemovidas.slice(0, estado.removidas));
    const piscando = new Set(estado.recemRemovidas.map((j) => m.idsRemovidas[j]));
    m.idsProj.forEach((id, i) => {
      const aresta = instancia.getElementById(id);
      const escondida = removidas.has(id) && !piscando.has(id);
      aresta.toggleClass("oculto", !(naProjecao && i < estado.projecao) || escondida);
      aresta.toggleClass("piscando", piscando.has(id));
      const a = aresta.source().id();
      const b = aresta.target().id();
      const ga = estado.grupos?.[a];
      const dentro = indices && ga !== undefined && ga === estado.grupos?.[b] && indices[a] != null;
      if (dentro) {
        aresta.data("color", communityStyle(indices[a] as number).color);
        aresta.addClass("intra");
      } else {
        aresta.removeClass("intra");
      }
    });
  });

  // Posições: anima ao trocar de grafo; fora de ordem (arrastar o controle), salta.
  if (posicaoRef.current !== alvo) {
    const primeira = posicaoRef.current === null;
    posicaoRef.current = alvo;
    instancia.stop(true);
    const animar = !primeira && !movimentoReduzido();
    const destinos: Position[] = [];
    instancia.nodes().forEach((n) => {
      const destino = posicoes.get(n.id());
      if (!destino) return;
      if (naProjecao ? m.mantidos.has(n.id()) : true) destinos.push(destino);
      if (animar) n.animate({ position: destino }, { duration: DURACAO_MOVIMENTO_MS, easing: "ease-in-out" });
      else n.position(destino);
    });
    // As colunas levam o nome dos nós dos lados; a projeção, só a folga da bolha.
    const folga = Math.min(150, instancia.width() * 0.2);
    vistaPara(instancia, destinos, naProjecao ? { x: 50, y: 50 } : { x: folga, y: 40 }, animar);
  }
}
