/**
 * Laboratório ao vivo — ADR-0013.
 *
 * Escolhe uma turma (a de Computação gerada na hora, ou uma amostra de
 * um dataset real), o tipo de projeção e o algoritmo; o servidor monta a
 * rede **de verdade** em menos de alguns segundos e a tela conta o que
 * aconteceu, quadro a quadro: matrículas, projeção, algoritmo, resultado.
 *
 * **Nada roda sozinho.** A rede só é montada quando o visitante aperta
 * ▶; mudar um controle depois disso apenas avisa que a tela ficou para
 * trás (o visitante costuma mexer em mais de um antes de querer rodar de
 * novo), e o próximo ▶ monta de novo. O controle de tempo anda para os
 * dois lados, e o resultado fica à mão para quem quiser pular a animação.
 */

import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";

import { ApiError, api } from "../api";
import {
  ETAPAS,
  duracaoDoQuadro,
  estadoDoQuadro,
  montarQuadros,
  type Etapa,
} from "../lab/frames";
import { acaoDoTocar, chaveDaTurma, mesmaBase } from "../lab/pedido";
import { jaVisto, marcarVisto, type NomeDoTour } from "../tour/estado";
import type {
  CentralityMetric,
  GraphResponse,
  LabOptions,
  LabRequest,
  LabRun,
  RoleId,
} from "../types";
import { ControlesZoom } from "./ControlesZoom";
import { idsDoSinal, type SinalFiltro } from "./Sinais";
import { ErrorBoundary } from "./ErrorBoundary";
import { LabCanvas, type LabCanvasHandle } from "./LabCanvas";
import { type ComparacaoItem, NOME_ALGORITMO, PainelEtapa, PainelResultado } from "./LabPaineis";
import { NodePanel } from "./NodePanel";
import { Seletor } from "./Seletor";

type Carga =
  | { status: "ocioso" }
  | { status: "carregando" }
  | { status: "pronto"; run: LabRun }
  | { status: "erro"; mensagem: string };

const PADRAO: LabRequest = {
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

const METRICAS: { id: CentralityMetric; nome: string }[] = [
  { id: "degree", nome: "Grau" },
  { id: "betweenness", nome: "Intermediação" },
  { id: "eigenvector", nome: "Autovetor" },
];

const movimentoReduzido = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function ControleDeslizante(props: {
  rotulo: string;
  valor: number;
  min: number;
  max: number;
  passo: number;
  formato: (v: number) => string;
  ajuda?: string;
  onChange: (v: number) => void;
}) {
  return (
    <label className="deslizante" title={props.ajuda}>
      <span className="deslizante-topo">
        <span>{props.rotulo}</span>
        <b>{props.formato(props.valor)}</b>
      </span>
      <input
        type="range"
        min={props.min}
        max={props.max}
        step={props.passo}
        value={props.valor}
        onChange={(e) => props.onChange(Number(e.target.value))}
      />
      {props.ajuda && <span className="deslizante-ajuda">{props.ajuda}</span>}
    </label>
  );
}

function Passo(props: { n: number; titulo: string; ajuda: string }) {
  return (
    <header className="passo">
      <span className="passo-num" aria-hidden="true">{props.n}</span>
      <div className="passo-texto">
        <h2>{props.titulo}</h2>
        <p>{props.ajuda}</p>
      </div>
    </header>
  );
}

function Segmentado<T extends string>(props: {
  nome: string;
  valor: T;
  opcoes: { id: T; nome: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <div className="segmentado lab-segmentado" role="radiogroup" aria-label={props.nome}>
      {props.opcoes.map((o) => (
        <button
          key={o.id}
          type="button"
          role="radio"
          aria-checked={props.valor === o.id}
          className={props.valor === o.id ? "ativo" : ""}
          onClick={() => props.onChange(o.id)}
        >
          <span className="radio-marca" aria-hidden="true" />
          {o.nome}
        </button>
      ))}
    </div>
  );
}

export function LabView({ tema, abrirTour }: { tema: "light" | "dark"; abrirTour: (nome: NomeDoTour) => void }) {
  const [opcoes, setOpcoes] = useState<LabOptions | null>(null);
  const [pedido, setPedido] = useState<LabRequest>(PADRAO);
  const [carga, setCarga] = useState<Carga>({ status: "ocioso" });
  /** O pedido que gerou o que está na tela; os controles podem já ter saído dele. */
  const [montado, setMontado] = useState<LabRequest | null>(null);
  const [executando, setExecutando] = useState(false);
  const [conviteVisto, setConviteVisto] = useState(() => jaVisto("resultado"));
  const [indice, setIndice] = useState(0);
  const [tocando, setTocando] = useState(false);
  const [velocidade, setVelocidade] = useState(1);
  const [selecionado, setSelecionado] = useState<string | null>(null);
  const [foco, setFoco] = useState<number | null>(null);
  const [papel, setPapel] = useState<RoleId | null>(null);
  const [sinal, setSinal] = useState<SinalFiltro | null>(null);
  const [metrica, setMetrica] = useState<CentralityMetric | null>("degree");
  const [bolhas, setBolhas] = useState(true);
  const [plantadas, setPlantadas] = useState(false);
  const [desfecho, setDesfecho] = useState(false);
  const [historico, setHistorico] = useState<Record<string, ComparacaoItem[]>>({});
  const canvasRef = useRef<LabCanvasHandle>(null);
  const ultimoPedido = useRef(0);

  useEffect(() => {
    api.labOptions().then(setOpcoes).catch(() => setOpcoes(null));
  }, []);

  // Monta a rede com o que está nos controles. Só a resposta mais recente vale.
  const executar = useCallback(() => {
    const numero = ++ultimoPedido.current;
    const enviado = pedido;
    setExecutando(true);
    api
      .labRun(enviado)
      .then((run) => {
        if (numero !== ultimoPedido.current) return;
        setExecutando(false);
        setCarga({ status: "pronto", run });
        setMontado(enviado);
        setSelecionado(null);
        setFoco(null);
        setPapel(null);
        setSinal(null);
        setPlantadas(false);
        setDesfecho(false);
        setIndice(0);
        // Com movimento reduzido não há animação: vai direto ao resultado.
        if (movimentoReduzido()) {
          setIndice(montarQuadros(run).length - 1);
          setTocando(false);
        } else {
          setTocando(true);
        }
        const chave = chaveDaTurma(enviado);
        setHistorico((h) => ({
          ...h,
          [chave]: [
            ...(h[chave] ?? []).filter((c) => c.algoritmo !== run.request.algorithm),
            {
              algoritmo: run.request.algorithm,
              q: run.result.q,
              grupos: run.result.n_communities,
              segundos: run.result.runtime_s,
              status: run.result.status,
            },
          ],
        }));
      })
      .catch((erro: unknown) => {
        if (numero !== ultimoPedido.current) return;
        setExecutando(false);
        setTocando(false);
        setMontado(null);
        setCarga({
          status: "erro",
          mensagem: erro instanceof ApiError ? erro.message : "Não foi possível montar a rede.",
        });
      });
  }, [pedido]);

  const run = carga.status === "pronto" ? carga.run : null;
  const quadros = useMemo(() => (run ? montarQuadros(run) : []), [run]);
  const quadro = quadros[Math.min(indice, quadros.length - 1)];
  const estado = useMemo(() => (run && quadro ? estadoDoQuadro(run, quadro) : null), [run, quadro]);

  // O tempo anda sozinho enquanto `tocando`; cada quadro tem a sua duração.
  useEffect(() => {
    if (!tocando || !run || !quadro) return;
    if (indice >= quadros.length - 1) {
      setTocando(false);
      return;
    }
    const espera = Math.max(duracaoDoQuadro(run, quadro) / velocidade, 16);
    const id = window.setTimeout(() => setIndice((i) => Math.min(i + 1, quadros.length - 1)), espera);
    return () => window.clearTimeout(id);
  }, [tocando, indice, quadros, quadro, run, velocidade]);

  const ir = useCallback(
    (i: number) => {
      setTocando(false);
      setIndice(Math.max(0, Math.min(i, quadros.length - 1)));
    },
    [quadros.length],
  );
  /** ▶ monta a rede quando não há nada na tela ou os controles mudaram; senão, toca e pausa. */
  const montarOuTocar = acaoDoTocar(montado, pedido);
  const alternar = () => {
    if (executando) return;
    if (montarOuTocar === "montar") {
      executar();
      return;
    }
    if (!run) return;
    if (indice >= quadros.length - 1) {
      setIndice(0);
      setTocando(true);
    } else {
      setTocando((t) => !t);
    }
  };
  const irParaEtapa = (etapa: Etapa) => ir(Math.max(0, quadros.findIndex((q) => q.etapa === etapa)));

  const atalhos = (e: KeyboardEvent<HTMLElement>) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const acoes: Record<string, () => void> = {
      " ": alternar,
      ArrowRight: () => ir(indice + 1),
      ArrowLeft: () => ir(indice - 1),
      Home: () => ir(0),
      End: () => ir(quadros.length - 1),
      "+": () => canvasRef.current?.aproximar(),
      "=": () => canvasRef.current?.aproximar(),
      "-": () => canvasRef.current?.afastar(),
      "0": () => canvasRef.current?.centralizar(),
    };
    const acao = acoes[e.key];
    if (!acao) return;
    e.preventDefault();
    acao();
  };

  const ajustar = (parte: Partial<LabRequest>) => setPedido((p) => ({ ...p, ...parte }));
  const sortear = () => ajustar({ seed: 1 + Math.floor(Math.random() * 9998) });

  const grafo = useMemo<GraphResponse | null>(
    () =>
      run && {
        dataset: run.source.id,
        projection_id: `${run.projection.side}_${run.projection.weighting}`,
        spec: {},
        nodes: run.projection.nodes,
        edges: run.projection.edges,
        truncation: {
          truncated: false,
          max_edges: run.projection.edges.length,
          n_nodes: run.projection.nodes.length,
          n_edges_total: run.projection.edges.length,
          n_edges_returned: run.projection.edges.length,
          criterion: "backbone",
          k_per_node: null,
        },
        community: run.result.membership,
        centrality: run.centrality,
      },
    [run],
  );
  const nomes = useMemo(
    () => Object.fromEntries((run?.insight.communities ?? []).map((c) => [c.id, c.name])),
    [run],
  );
  const metricasDisponiveis = METRICAS.filter((m) => run?.centrality[m.id]);
  const demo = pedido.source === "demo";
  const comparacao = historico[chaveDaTurma(montado ?? pedido)] ?? [];
  const pendente = run !== null && montarOuTocar === "montar";
  /** Os limites do corte de ligações valem para a rede que está na tela, não para a que os controles descrevem. */
  const baseIgual = montado === null || mesmaBase(montado, pedido);
  const faixaDePeso = run?.projection.weight_range ?? [0, 0];
  const noResultado = estado?.etapa === "resultado";
  const realce = useMemo(() => idsDoSinal(run?.insight.signals, sinal), [run, sinal]);

  return (
    <>
      <main className="palco lab-palco" onKeyDown={atalhos}>
        <section className="figura-area lab-figura-area" aria-label="Laboratório: montagem da rede">
          <nav className="lab-etapas" aria-label="Etapas">
            <div className="lab-etapa-chips" data-tour="etapas">
              {ETAPAS.map((e, i) => (
                <button
                  key={e.id}
                  type="button"
                  className={`lab-etapa-chip ${estado?.etapa === e.id ? "ativa" : ""}`}
                  aria-current={estado?.etapa === e.id ? "step" : undefined}
                  disabled={!run}
                  onClick={() => irParaEtapa(e.id)}
                >
                  <span aria-hidden="true">{i + 1}</span>
                  {e.nome}
                </button>
              ))}
            </div>
            <div className="lab-algoritmo" role="radiogroup" aria-label="Algoritmo de comunidades" data-tour="algoritmo">
              <span className="lab-algoritmo-rotulo">Algoritmo</span>
              {(["louvain", "girvan_newman"] as const).map((a) => (
                <button
                  key={a}
                  type="button"
                  role="radio"
                  aria-checked={pedido.algorithm === a}
                  className={pedido.algorithm === a ? "ativo" : ""}
                  title={
                    a === "louvain"
                      ? "Rápido: cada nó entra no grupo que mais aumenta a modularidade."
                      : "Lento: apaga a ligação-ponte mais usada até a rede se partir."
                  }
                  onClick={() => ajustar({ algorithm: a })}
                >
                  {NOME_ALGORITMO[a]}
                </button>
              ))}
            </div>
          </nav>

          <div className="figura lab-figura" data-tour="grafo">
            <div className="palco-conteudo">
              {executando && !run && (
                <div className="vazio vazio-carregando" role="status" aria-live="polite">
                  <h2>Montando a rede…</h2>
                  <p>Gerando a turma e rodando o algoritmo de verdade.</p>
                  <span className="fio" aria-hidden="true"><span /></span>
                </div>
              )}
              {carga.status === "ocioso" && !executando && (
                <div className="vazio vazio-ocioso">
                  <svg viewBox="0 0 150 90" fill="none" stroke="currentColor" strokeWidth="1.2" aria-hidden="true">
                    <path d="M22 18 128 24M22 18 128 45M22 45 128 24M22 45 128 66M22 72 128 45M22 72 128 66" opacity="0.55" />
                    {[18, 45, 72].map((y) => <circle key={`a${y}`} cx="22" cy={y} r="6" fill="var(--sheet)" />)}
                    {[24, 45, 66].map((y) => <rect key={`d${y}`} x="122" y={y - 6} width="12" height="12" rx="2" fill="var(--sheet)" />)}
                  </svg>
                  <h2>Aperte ▶ para montar a rede</h2>
                  <p>
                    Ajuste a turma e o algoritmo nos controles ao lado e, quando quiser, monte a rede. Nada roda antes
                    disso.
                  </p>
                  <p className="ocioso-resumo">
                    {pedido.students} alunos · {NOME_ALGORITMO[pedido.algorithm]} ·{" "}
                    {pedido.side === "student" ? "ligando alunos" : "ligando disciplinas"}
                  </p>
                  <button type="button" className="botao-montar" onClick={executar}>
                    <span aria-hidden="true">▶</span> Montar a rede
                  </button>
                </div>
              )}
              {carga.status === "erro" && (
                <div className="vazio vazio-erro" role="alert">
                  <h2>Não deu para montar</h2>
                  <p>{carga.mensagem}</p>
                  <p>Ajuste os controles e aperte ▶ para tentar de novo.</p>
                </div>
              )}
              {run && estado && (
                <ErrorBoundary resetKey={`${run.request.seed}-${run.request.algorithm}-${run.timing.total_s}`}>
                  <LabCanvas
                    ref={canvasRef}
                    run={run}
                    estado={estado}
                    metrica={metrica}
                    tema={tema}
                    selected={selecionado}
                    onSelect={setSelecionado}
                    foco={foco}
                    papel={papel}
                    bolhas={bolhas}
                    plantadas={plantadas}
                    nomes={nomes}
                    papeis={run.insight.roles}
                    realce={realce}
                  />
                </ErrorBoundary>
              )}
            </div>
            {run && (
              <ControlesZoom
                aoAproximar={() => canvasRef.current?.aproximar()}
                aoAfastar={() => canvasRef.current?.afastar()}
                aoCentralizar={() => canvasRef.current?.centralizar()}
              />
            )}
            {executando && run && <span className="lab-recalculando" role="status">recalculando…</span>}
            {pendente && !executando && (
              <div className="lab-pendente" role="status">
                <span>Você mudou a configuração.</span>
                <button type="button" onClick={executar}>▶ Montar de novo</button>
              </div>
            )}
          </div>

          <div className="lab-controle" role="group" aria-label="Controle da animação">
            <button type="button" onClick={() => ir(0)} aria-label="Voltar ao início" title="Início (Home)" disabled={!run}>⏮</button>
            <button type="button" onClick={() => ir(indice - 1)} aria-label="Quadro anterior" title="Anterior (←)" disabled={!run}>◀</button>
            <button
              type="button"
              className={`lab-tocar ${montarOuTocar === "montar" && !executando ? "chama" : ""}`}
              data-tour="tocar"
              onClick={alternar}
              aria-label={montarOuTocar === "montar" ? "Montar a rede" : tocando ? "Pausar" : "Tocar"}
              title={montarOuTocar === "montar" ? "Montar a rede com estes controles (espaço)" : "Tocar ou pausar (espaço)"}
              disabled={executando}
            >
              {montarOuTocar === "tocar" && tocando ? "⏸" : "▶"}
            </button>
            <button type="button" onClick={() => ir(indice + 1)} aria-label="Próximo quadro" title="Próximo (→)" disabled={!run}>▶|</button>
            <button type="button" onClick={() => ir(quadros.length - 1)} aria-label="Ir ao resultado" title="Resultado (End)" disabled={!run}>⏭</button>
            <input
              className="lab-linha"
              type="range"
              min={0}
              max={Math.max(quadros.length - 1, 0)}
              value={Math.min(indice, Math.max(quadros.length - 1, 0))}
              onChange={(e) => ir(Number(e.target.value))}
              aria-label="Posição na animação"
              disabled={!run}
            />
            <label className="lab-velocidade">
              Velocidade
              <select value={velocidade} onChange={(e) => setVelocidade(Number(e.target.value))}>
                {[0.5, 1, 2, 4].map((v) => <option key={v} value={v}>{v}×</option>)}
              </select>
            </label>
          </div>
          <p className="legenda-fig lab-legenda">
            {run ? (
              <>
                <b>Figura 2.</b> {run.source.title}: {run.projection.nodes.length}{" "}
                {run.projection.side === "student" ? "alunos" : "disciplinas"},{" "}
                {run.projection.edges.length.toLocaleString("pt-BR")} ligações, montados agora com{" "}
                {NOME_ALGORITMO[run.request.algorithm]}. Espaço toca e pausa; ← e → andam quadro a quadro.
              </>
            ) : (
              "Escolha a turma e aperte ▶ para ver o grafo nascer."
            )}
          </p>
        </section>

        <aside className="nota-lateral lab-lateral" aria-label="Narração e resultado" data-tour="narracao">
          <AnimatePresence>
            {run && grafo && selecionado && (
              <NodePanel
                graph={grafo}
                membership={run.result.membership}
                nodeId={selecionado}
                onSelect={setSelecionado}
                leitura={run.insight}
              />
            )}
          </AnimatePresence>
          {!selecionado && run && estado && (
            <motion.div key={estado.etapa === "resultado" ? "res" : "etapa"} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.2 }}>
              {noResultado ? (
                <PainelResultado
                  run={run}
                  foco={foco}
                  onFoco={setFoco}
                  papel={papel}
                  onPapel={(p) => {
                    setPapel(p);
                    if (p) setSinal(null);
                  }}
                  sinal={sinal}
                  onSinal={(f) => {
                    setSinal(f);
                    if (f) setPapel(null);
                  }}
                  onSelecionar={setSelecionado}
                  metrica={metrica}
                  metricas={metricasDisponiveis}
                  onMetrica={setMetrica}
                  bolhas={bolhas}
                  onBolhas={setBolhas}
                  plantadas={plantadas}
                  onPlantadas={setPlantadas}
                  desfecho={desfecho}
                  onDesfecho={setDesfecho}
                  comparacao={comparacao}
                  convite={!conviteVisto}
                  onEntender={() => {
                    marcarVisto("resultado");
                    setConviteVisto(true);
                    abrirTour("resultado");
                  }}
                  onDispensarConvite={() => {
                    marcarVisto("resultado");
                    setConviteVisto(true);
                  }}
                />
              ) : (
                <PainelEtapa run={run} estado={estado} />
              )}
            </motion.div>
          )}
          {!run && carga.status !== "erro" && (
            <p className="inspetor-vazio">Depois que você montar a rede, a narração de cada etapa aparece aqui.</p>
          )}
        </aside>
      </main>

      <aside className="painel" aria-label="Controles do laboratório">
        <section className="cartao" data-tour="turma">
          <Passo n={1} titulo="Turma" ajuda="De onde vêm os alunos." />
          <div className="campo">
            <Seletor
              nome="Fonte dos dados"
              value={pedido.source}
              opcoes={(opcoes?.sources ?? [{ id: "demo", title: "Turma de Computação (fictícia)", fictional: true }]).map((s) => ({
                value: s.id,
                rotulo: s.fictional ? "Turma de Computação (fictícia)" : s.title,
                id: s.fictional ? undefined : "amostra",
              }))}
              onChange={(source) => ajustar({ source, min_weight: null })}
            />
          </div>
          <div className="campo lab-campo">
            <ControleDeslizante
              rotulo="Alunos"
              valor={pedido.students}
              min={opcoes?.min_students ?? 24}
              max={opcoes?.max_students ?? 75}
              passo={3}
              formato={(v) => `${v}`}
              ajuda={demo ? "Quanto maior a turma, mais tempo o Girvan–Newman leva." : "Amostra sorteada do dataset."}
              onChange={(students) => ajustar({ students })}
            />
            {demo && (
              <ControleDeslizante
                rotulo="Mistura entre áreas"
                valor={pedido.noise}
                min={0}
                max={0.6}
                passo={0.05}
                formato={(v) => `${Math.round(v * 100)}%`}
                ajuda="Alunos que cursam também disciplinas de fora da sua área. Com muita mistura, os grupos ficam difíceis de achar."
                onChange={(noise) => ajustar({ noise })}
              />
            )}
            <button type="button" className="botao-secundario" onClick={sortear} title={`Turma nº ${pedido.seed}`}>
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M3 12a9 9 0 0 1 15.5-6.2L21 8M21 3v5h-5M21 12a9 9 0 0 1-15.5 6.2L3 16M3 21v-5h5" />
              </svg>
              Sortear nova turma
            </button>
            <p className="dim lab-nota">turma nº {pedido.seed}</p>
          </div>
        </section>

        <section className="cartao" data-tour="rede">
          <Passo n={2} titulo="Rede" ajuda="O que ligar a quê." />
          <div className="campo lab-campo">
            <Segmentado
              nome="O que projetar"
              valor={pedido.side}
              opcoes={[{ id: "student", nome: "Alunos" }, { id: "discipline", nome: "Disciplinas" }]}
              onChange={(side) => ajustar({ side, min_weight: null })}
            />
            <Segmentado
              nome="Ponderação"
              valor={pedido.weighting}
              opcoes={[{ id: "simple", nome: "Simples" }, { id: "resource_allocation", nome: "Alocação de recursos" }]}
              onChange={(weighting) => ajustar({ weighting, min_weight: null })}
            />
            {run && baseIgual && faixaDePeso[1] > faixaDePeso[0] && (
              <ControleDeslizante
                rotulo="Ligação mínima"
                valor={pedido.min_weight ?? faixaDePeso[0]}
                min={faixaDePeso[0]}
                max={faixaDePeso[1]}
                passo={Math.max((faixaDePeso[1] - faixaDePeso[0]) / 40, 0.0001)}
                formato={(v) => (pedido.min_weight === null ? "todas" : v.toLocaleString("pt-BR", { maximumFractionDigits: 2 }))}
                ajuda="Corta as ligações mais fracas — é como a rede real fica legível."
                onChange={(v) => ajustar({ min_weight: v <= faixaDePeso[0] ? null : v })}
              />
            )}
            {run && baseIgual && run.projection.suggested_min_weight !== null && pedido.min_weight === null && (
              <button
                type="button"
                className="botao-secundario"
                onClick={() => ajustar({ min_weight: run.projection.suggested_min_weight })}
                title="A rede é quase completa: manter só as ligações mais fortes deixa os grupos visíveis"
              >
                Manter só as 30% mais fortes
              </button>
            )}
          </div>
        </section>

        {run && (
          <section className="cartao lab-rodape-controles">
            <p className="dim lab-nota">
              Calculado de verdade agora, em{" "}
              {run.timing.total_s < 0.01
                ? "menos de 0,01 s"
                : `${run.timing.total_s.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} s`}
              {run.source.fictional ? ", com dados fictícios" : ""}.
            </p>
          </section>
        )}
      </aside>
    </>
  );
}
