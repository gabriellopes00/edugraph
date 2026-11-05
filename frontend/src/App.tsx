/**
 * Aplicação — Frente C, spec C-05.
 *
 * Os seletores são montados a partir de `/datasets`, sem nome de dataset
 * embutido no código: o que estiver em disco sob as raízes da API
 * aparece aqui.
 *
 * Duas abas: o **laboratório** (`LabView`), que monta uma rede pequena
 * na hora e conta a montagem em etapas (ADR-0013), e o **explorador**,
 * que lê os resultados já calculados em disco.
 *
 * Duas requisições por tela no explorador, de propósito:
 *
 * - a **projeção**, com as centralidades embutidas, muda quando muda o
 *   dataset ou a projeção — e só então o grafo é redesenhado;
 * - a **partição** vem à parte, para que trocar a cor não recarregue nem
 *   re-diagrame o grafo: só os nós mudam de cor, com transição.
 */

import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { AnimatePresence, MotionConfig, motion } from "framer-motion";

import { ApiError, api } from "./api";
import { Alca, useColunas } from "./components/Alca";
import { CommunityLegend, LegendaDeDesfecho } from "./components/CommunityLegend";
import { ControlesZoom } from "./components/ControlesZoom";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { GraphView, type GraphViewHandle } from "./components/GraphView";
import { LabView } from "./components/LabView";
import { jaVisto, marcarVisto, opcoesDaUrl, type NomeDoTour } from "./tour/estado";
import { PASSOS } from "./tour/passos";
import { Tour } from "./tour/Tour";
import { NodePanel } from "./components/NodePanel";
import { Conferencia, idsDoSinal, PainelSinais, type SinalFiltro } from "./components/Sinais";
import { Seletor } from "./components/Seletor";
import { StatsBar } from "./components/StatsBar";
import type {
  CentralityMetric,
  DatasetSummary,
  GraphResponse,
  HealthResponse,
  InsightResponse,
  OutcomesResponse,
  PartitionResponse,
  RoleId,
} from "./types";

type Estado<T> =
  | { status: "carregando" }
  | { status: "pronto"; dados: T }
  | { status: "erro"; erro: ApiError };

const METRICAS: { id: CentralityMetric; nome: string }[] = [
  { id: "degree", nome: "Grau" },
  { id: "betweenness", nome: "Intermediação" },
  { id: "eigenvector", nome: "Autovetor" },
];

/**
 * Onde o explorador abre: o primeiro par dataset/projeção que já tem partição
 * **e** centralidade. Abrir num dataset incompleto mostraria um grafo sem cor
 * nem tamanho, e é a primeira coisa que a banca veria.
 */
function escolhaInicial(lista: DatasetSummary[]): { dataset: string; projecao: string | null } | null {
  for (const d of lista) {
    const completas = d.projections.filter(
      (p) => d.centralities.includes(p) && d.partitions.some((id) => id.endsWith(`__${p}`)),
    );
    // Entre as completas, a de alunos primeiro: é a que conta a história (grupos de
    // alunos); a de disciplinas, em sintético, tem só 7 nós.
    const completa = completas.find((p) => p === "student_simple") ?? completas.find((p) => p.startsWith("student")) ?? completas[0];
    if (completa) return { dataset: d.dataset, projecao: completa };
  }
  const parcial = lista.find((d) => d.projections.length > 0) ?? lista[0];
  return parcial ? { dataset: parcial.dataset, projecao: parcial.projections[0] ?? null } : null;
}

/** Partições da projeção ativa: `<algoritmo>__<projection_id>`, Louvain primeiro. */
function particoesDa(resumo: DatasetSummary | null, projecao: string | null): string[] {
  if (!resumo || !projecao) return [];
  return resumo.partitions
    .filter((id) => id.endsWith(`__${projecao}`))
    .sort((a, b) => Number(!a.startsWith("louvain")) - Number(!b.startsWith("louvain")) || a.localeCompare(b));
}

type Tema = "light" | "dark";
const CHAVE_TEMA = "edugraph-tema";

type Aba = "laboratorio" | "explorar";
const ABAS: { id: Aba; nome: string; ajuda: string }[] = [
  { id: "laboratorio", nome: "Laboratório ao vivo", ajuda: "Monta uma rede pequena na hora" },
  { id: "explorar", nome: "Explorar resultados", ajuda: "Os resultados do OULAD já calculados" },
];

/** A aba vem do endereço (`#explorar`), para poder abrir e compartilhar direto nela. */
function abaInicial(): Aba {
  return window.location.hash === "#explorar" ? "explorar" : "laboratorio";
}

const PAPEIS: RoleId[] = ["referencia", "conector", "ponte", "periferico"];

/** O atributo já foi posto por `index.html` antes da primeira pintura. */
function temaInicial(): Tema {
  return document.documentElement.dataset.theme === "light" ? "light" : "dark";
}

export default function App() {
  const [tema, setTema] = useState<Tema>(temaInicial);
  const [aba, setAba] = useState<Aba>(abaInicial);
  const [apresentando, setApresentando] = useState(false);
  /** Tour aberto agora, se houver. O de cada tela abre sozinho na primeira visita. */
  const [tour, setTour] = useState<NomeDoTour | null>(null);
  const tourForcado = useRef(false);
  // Colunas laterais retráteis. Com o tour aberto ficam as duas à vista: ele aponta para elas.
  const { abertas, definir } = useColunas();
  const esquerdaAberta = abertas.esquerda || tour !== null;
  const direitaAberta = abertas.direita || tour !== null;
  const alternarColuna = useCallback(
    (lado: "esquerda" | "direita") => definir(lado, !abertas[lado]),
    [abertas, definir],
  );
  const abrirDireita = useCallback(() => definir("direita", true), [definir]);

  useEffect(() => {
    const opcoes = opcoesDaUrl(window.location.search);
    if (opcoes.desligar) return;
    const nome: NomeDoTour = aba === "laboratorio" ? "lab" : "explorador";
    const forcar = opcoes.forcar && aba === "laboratorio" && !tourForcado.current;
    if (!forcar && jaVisto(nome)) return;
    tourForcado.current = true;
    // Dá tempo de a tela se montar (e, no explorador, de os cartões chegarem).
    const espera = window.setTimeout(() => setTour(nome), aba === "laboratorio" ? 500 : 1500);
    return () => window.clearTimeout(espera);
  }, [aba]);

  const fecharTour = useCallback((nome: NomeDoTour) => {
    marcarVisto(nome);
    setTour(null);
  }, []);

  const trocarAba = (nova: Aba) => {
    setAba(nova);
    window.history.replaceState(null, "", nova === "explorar" ? "#explorar" : "#laboratorio");
  };

  /** Tela cheia, sem cabeçalho nem rodapé e com letra maior: para a banca. */
  const alternarApresentacao = useCallback(() => {
    const entrar = !document.fullscreenElement;
    setApresentando(entrar);
    const pedido = entrar
      ? document.documentElement.requestFullscreen?.()
      : document.exitFullscreen?.();
    pedido?.catch(() => {
      /* sem tela cheia (iframe ou política do navegador): o modo ainda vale na janela */
    });
  }, []);
  useEffect(() => {
    const aoSair = () => !document.fullscreenElement && setApresentando(false);
    document.addEventListener("fullscreenchange", aoSair);
    return () => document.removeEventListener("fullscreenchange", aoSair);
  }, []);
  const grafoRef = useRef<GraphViewHandle>(null);
  // Timeout que tira a classe de transição do tema; só pode haver um.
  const fimTransicaoTema = useRef(0);

  // Ao desmontar: cancela o timeout e não deixa a classe para trás.
  useEffect(
    () => () => {
      window.clearTimeout(fimTransicaoTema.current);
      document.documentElement.classList.remove("tema-trocando");
    },
    [],
  );
  const [health, setHealth] = useState<Estado<HealthResponse>>({ status: "carregando" });
  const [datasets, setDatasets] = useState<Estado<DatasetSummary[]>>({ status: "carregando" });
  const [datasetAtivo, setDatasetAtivo] = useState<string | null>(null);
  const [projecaoAtiva, setProjecaoAtiva] = useState<string | null>(null);
  const [particaoAtiva, setParticaoAtiva] = useState<string | null>(null);
  const [metricaAtiva, setMetricaAtiva] = useState<CentralityMetric | null>("degree");
  const [selecionado, setSelecionado] = useState<string | null>(null);
  const [grafo, setGrafo] = useState<Estado<GraphResponse> | null>(null);
  const [particao, setParticao] = useState<PartitionResponse | null>(null);
  const [leitura, setLeitura] = useState<InsightResponse | null>(null);
  const [desfechos, setDesfechos] = useState<OutcomesResponse | null>(null);
  const [mostrarDesfecho, setMostrarDesfecho] = useState(false);
  const [foco, setFoco] = useState<number | null>(null);
  const [papel, setPapel] = useState<RoleId | null>(null);
  const [sinal, setSinal] = useState<SinalFiltro | null>(null);
  const [bolhas, setBolhas] = useState(true);

  // Escolher um nó com os detalhes fechados abre a coluna: é o que se queria ver.
  useEffect(() => {
    if (selecionado) abrirDireita();
  }, [selecionado, abrirDireita]);

  useEffect(() => {
    api
      .health()
      .then((dados) => setHealth({ status: "pronto", dados }))
      .catch((erro: ApiError) => setHealth({ status: "erro", erro }));

    api
      .datasets()
      .then(({ datasets: lista }) => {
        setDatasets({ status: "pronto", dados: lista });
        const inicial = escolhaInicial(lista);
        if (inicial) {
          setDatasetAtivo(inicial.dataset);
          setProjecaoAtiva(inicial.projecao);
        }
      })
      .catch((erro: ApiError) => setDatasets({ status: "erro", erro }));
  }, []);

  /**
   * Alterna claro/escuro. O atributo é posto **antes** de `setTema`: o canvas
   * do grafo lê as cores dos tokens CSS ao reagir à troca, então eles já
   * precisam valer. A transição curta só roda sem movimento reduzido.
   */
  const alternarTema = () => {
    const novo: Tema = tema === "light" ? "dark" : "light";
    const raiz = document.documentElement;
    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      raiz.classList.add("tema-trocando");
      window.clearTimeout(fimTransicaoTema.current);
      fimTransicaoTema.current = window.setTimeout(() => raiz.classList.remove("tema-trocando"), 320);
    }
    raiz.dataset.theme = novo;
    try {
      localStorage.setItem(CHAVE_TEMA, novo);
    } catch {
      /* sem armazenamento: a escolha vale só nesta sessão */
    }
    setTema(novo);
  };

  // F alterna o modo apresentação, de qualquer lugar fora de campos de texto.
  useEffect(() => {
    const aoTeclar = (e: globalThis.KeyboardEvent) => {
      const alvo = e.target as HTMLElement | null;
      if (e.ctrlKey || e.metaKey || e.altKey || e.key.toLowerCase() !== "f") return;
      if (alvo && /^(INPUT|SELECT|TEXTAREA)$/.test(alvo.tagName)) return;
      alternarApresentacao();
    };
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [alternarApresentacao]);

  /** Atalhos de zoom: valem só com o foco dentro do palco (grafo, controles ou painel do nó). */
  const atalhosDoPalco = (event: KeyboardEvent<HTMLElement>) => {
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    const acao =
      event.key === "+" || event.key === "="
        ? grafoRef.current?.aproximar
        : event.key === "-" || event.key === "_"
          ? grafoRef.current?.afastar
          : event.key === "0"
            ? grafoRef.current?.centralizar
            : undefined;
    if (!acao) return;
    event.preventDefault();
    acao();
  };

  const resumoAtivo = useMemo(
    () =>
      datasets.status === "pronto"
        ? (datasets.dados.find((d) => d.dataset === datasetAtivo) ?? null)
        : null,
    [datasets, datasetAtivo],
  );
  const particoes = useMemo(
    () => particoesDa(resumoAtivo, projecaoAtiva),
    [resumoAtivo, projecaoAtiva],
  );

  // Ao trocar de projeção: a primeira partição dela, e nenhum nó selecionado.
  useEffect(() => {
    setParticaoAtiva(particoes[0] ?? null);
    setSelecionado(null);
  }, [particoes]);

  // A projeção, com as centralidades que existirem em disco.
  useEffect(() => {
    if (!datasetAtivo || !projecaoAtiva) {
      setGrafo(null);
      return;
    }
    let cancelado = false;
    const temCentralidade = resumoAtivo?.centralities.includes(projecaoAtiva) ?? false;
    const todas = METRICAS.map((m) => m.id);

    setGrafo({ status: "carregando" });
    (temCentralidade
      ? api.availableMetrics(datasetAtivo, projecaoAtiva, todas)
      : Promise.resolve<CentralityMetric[]>([])
    )
      .then((metrics) => api.projection(datasetAtivo, projecaoAtiva, { metrics }))
      .then((dados) => !cancelado && setGrafo({ status: "pronto", dados }))
      .catch((erro: ApiError) => !cancelado && setGrafo({ status: "erro", erro }));
    return () => {
      cancelado = true;
    };
  }, [datasetAtivo, projecaoAtiva, resumoAtivo]);

  // A partição, à parte: trocar a cor não redesenha o grafo.
  useEffect(() => {
    // Limpa já: sem isto a legenda e o Q da partição anterior ficam na
    // tela até a resposta nova chegar.
    setParticao(null);
    if (!datasetAtivo || !particaoAtiva) return;
    let cancelado = false;
    api
      .partition(datasetAtivo, particaoAtiva)
      .then((dados) => !cancelado && setParticao(dados))
      .catch(() => !cancelado && setParticao(null));
    return () => {
      cancelado = true;
    };
  }, [datasetAtivo, particaoAtiva]);

  // A leitura (nomes, papéis, frases) e o desfecho vêm à parte e **depois** do
  // grafo: pedir tudo junto fazia o servidor ler a mesma projeção duas vezes
  // ao mesmo tempo (no AVA do OULAD, o grafo demorava o dobro).
  const grafoPronto = grafo?.status === "pronto";
  useEffect(() => {
    setLeitura(null);
    setDesfechos(null);
    setMostrarDesfecho(false);
    setFoco(null);
    setPapel(null);
    setSinal(null);
    if (!datasetAtivo || !particaoAtiva || !grafoPronto) return;
    let cancelado = false;
    // Em fila, não em paralelo: o desfecho reaproveita a leitura que o servidor
    // acabou de fazer (os sinais por aluno), e pedir os dois juntos a repetiria.
    api
      .insight(datasetAtivo, particaoAtiva)
      .then((dados) => !cancelado && setLeitura(dados))
      .catch(() => undefined)
      .then(() => (cancelado ? null : api.outcomes(datasetAtivo, particaoAtiva)))
      .then((dados) => dados && !cancelado && setDesfechos(dados.rows.length > 0 ? dados : null))
      .catch(() => undefined);
    return () => {
      cancelado = true;
    };
  }, [datasetAtivo, particaoAtiva, grafoPronto]);

  const dadosGrafo = grafo?.status === "pronto" ? grafo.dados : null;
  const metricasDisponiveis = METRICAS.filter((m) => dadosGrafo?.centrality?.[m.id]);
  const realce = useMemo(() => idsDoSinal(leitura?.signals, sinal), [leitura, sinal]);
  const rotulosDosNos = useMemo(
    () => new Map((dadosGrafo?.nodes ?? []).map((n) => [n.id, n.label])),
    [dadosGrafo],
  );
  const membership = particao?.membership ?? null;
  const chaveMetricas = metricasDisponiveis.map((m) => m.id).join(",");
  const nomesDasComunidades = useMemo(
    () => Object.fromEntries((leitura?.communities ?? []).map((c) => [c.id, c.name])),
    [leitura],
  );

  // Se a métrica escolhida não existe nesta projeção, cai na primeira que existir.
  useEffect(() => {
    if (!dadosGrafo) return;
    const ids = chaveMetricas ? (chaveMetricas.split(",") as CentralityMetric[]) : [];
    setMetricaAtiva((atual) => (atual === null || ids.includes(atual) ? atual : (ids[0] ?? null)));
  }, [dadosGrafo, chaveMetricas]);

  return (
    <MotionConfig reducedMotion="user">
    <div className={`app ${apresentando ? "apresentando" : ""} ${esquerdaAberta ? "" : "esq-fechada"} ${direitaAberta ? "" : "dir-fechada"}`}>
      <header className="topo">
        <div className="hero">
          <p className="sobrelinha">Trabalho de Conclusão de Curso · Grupo 16 · UniAnchieta</p>
          <h1 title="Análise Topológica e Detecção de Comunidades em Redes Complexas">Análise Topológica e Detecção de Comunidades em Redes Complexas</h1>
          <p className="autores" title={AUTORES.join(", ")}>{AUTORES.join(", ")}</p>
          <nav className="abas" aria-label="Seções" data-tour="abas">
            {ABAS.map((a) => (
              <button
                key={a.id}
                type="button"
                className={aba === a.id ? "ativa" : ""}
                aria-current={aba === a.id ? "page" : undefined}
                title={a.ajuda}
                onClick={() => trocarAba(a.id)}
              >
                {a.nome}
              </button>
            ))}
          </nav>
        </div>
        <div className="topo-lado">
          <span className="wordmark"><Marca /><span className="wordmark-nome">edugraph</span></span>
          <div className="topo-status">
            <StatusApi estado={health} />
            <button type="button" className="tema-botao botao-tour" onClick={() => setTour(aba === "laboratorio" ? "lab" : "explorador")}
              title="Rever o tour desta tela" aria-label="Rever o tour desta tela">
              <b aria-hidden="true">?</b><span>Tour</span>
            </button>
            <button type="button" className="tema-botao botao-apresentar" aria-pressed={apresentando} onClick={alternarApresentacao}
              title="Tela cheia, com letra maior (F)">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" /></svg>
              Apresentar
            </button>
            <BotaoTema tema={tema} onAlternar={alternarTema} />
          </div>
        </div>
      </header>
      {aba === "laboratorio" ? (
        <LabView
          tema={tema}
          abrirTour={setTour}
          esquerdaAberta={esquerdaAberta}
          direitaAberta={direitaAberta}
          alternarColuna={alternarColuna}
          abrirDireita={abrirDireita}
        />
      ) : (
      <>
      <main className="palco" onKeyDown={atalhosDoPalco}>
        <section className="figura-area" aria-label="Figura da rede" data-tour="x-grafo">
          <Alca lado="esquerda" aberta={esquerdaAberta} rotulo="Controles" controla="coluna-esquerda" onAlternar={() => alternarColuna("esquerda")} />
          <Alca lado="direita" aberta={direitaAberta} rotulo="Detalhes" controla="coluna-direita" onAlternar={() => alternarColuna("direita")} />
          {dadosGrafo && <StatsBar graph={dadosGrafo} partition={particao} />}
          <div className="figura">
            <AnimatePresence mode="wait">
              <motion.div
                key={`${datasetAtivo}/${projecaoAtiva}/${grafo?.status}`}
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }} className="palco-conteudo"
              >
                {grafo === null && <Vazio tipo="vazio">Escolha um dataset e uma projeção para ver o grafo.</Vazio>}
                {grafo?.status === "carregando" && <Vazio tipo="carregando">{datasetAtivo} · {projecaoAtiva}</Vazio>}
                {grafo?.status === "erro" && <Vazio tipo="erro">{grafo.erro.message}</Vazio>}
                {dadosGrafo && (
                  <ErrorBoundary resetKey={`${datasetAtivo}/${projecaoAtiva}`}>
                    <GraphView ref={grafoRef} graph={dadosGrafo} membership={membership}
                      sizeBy={metricaAtiva} tema={tema} selected={selecionado} onSelect={setSelecionado}
                      foco={foco} papel={papel} papeis={leitura?.roles ?? null} realce={realce}
                      nomes={nomesDasComunidades} bolhas={bolhas} />
                  </ErrorBoundary>
                )}
              </motion.div>
            </AnimatePresence>
            {dadosGrafo && <ControlesZoom aoAproximar={() => grafoRef.current?.aproximar()}
              aoAfastar={() => grafoRef.current?.afastar()} aoCentralizar={() => grafoRef.current?.centralizar()} />}
          </div>
          <p className="legenda-fig">
            <b>Figura 1.</b> {ROTULO_PROJECAO[projecaoAtiva ?? ""] ?? "Rede educacional"}
            {datasetAtivo && <>, <i>{datasetAtivo}</i></>}. <b>Forma e cor</b>{" "}
            <span className="glifos-legenda"><Marca /></span> indicam a comunidade
            {particao && <> ({ROTULO_ALGORITMO[particao.algorithm] ?? particao.algorithm})</>}; a forma basta para ler em cinza.{" "}
            <b>Tamanho</b> {metricaAtiva ? `é ${METRICAS.find(m => m.id === metricaAtiva)?.nome.toLowerCase()}` : "é igual para todos os nós"}.{" "}
            <b>Espessura</b> da linha é o peso da ligação. Clique num nó para ver os detalhes.
          </p>
        </section>
        <aside className="nota-lateral" id="coluna-direita" aria-label="Detalhes do nó">
          {!(dadosGrafo && selecionado) && <p className="inspetor-vazio">Selecione um nó no grafo para ver comunidade, centralidades e vizinhos.</p>}
          <AnimatePresence>
            {dadosGrafo && selecionado && <NodePanel graph={dadosGrafo} membership={membership} nodeId={selecionado} onSelect={setSelecionado} leitura={leitura} />}
          </AnimatePresence>
        </aside>
      </main>
      <aside className="painel" id="coluna-esquerda" aria-label="Controles do grafo">
        <section className="cartao" data-tour="x-dados">
          <Passo n={1} titulo="Dados" ajuda="Conjunto lido do disco." />
          {datasets.status === "carregando" && (
            <p className="nota nota-carregando">
              carregando datasets…
            </p>
          )}
          {datasets.status === "erro" && (
            <p className="nota nota-erro" role="alert">
              API fora do ar: {datasets.erro.message}
              <br />
              <code>python -m edugraph api serve --root data/fixtures</code>
            </p>
          )}
          {datasets.status === "pronto" && (
            <Campo id={null}>
              <Seletor
                nome="Dataset"
                value={datasetAtivo ?? ""}
                titulo={datasetAtivo ?? undefined}
                opcoes={datasets.dados.map((d) => ({ value: d.dataset, rotulo: d.dataset }))}
                onChange={(escolhido) => {
                  setDatasetAtivo(escolhido);
                  const resumo = datasets.dados.find((d) => d.dataset === escolhido);
                  setProjecaoAtiva(resumo?.projections[0] ?? null);
                }}
              />
            </Campo>
          )}
        </section>

        {resumoAtivo && (
          <>
            <section className="cartao" data-tour="x-projecao">
              <Passo
                n={2}
                titulo="Projeção"
                ajuda="Rede de um só tipo de nó."
              />
              {resumoAtivo.projections.length === 0 ? (
                <p className="nota">nenhuma projeção neste dataset</p>
              ) : (
                <Campo id={ROTULO_PROJECAO[projecaoAtiva ?? ""] ? projecaoAtiva : null}>
                  <Seletor
                    nome="Projeção"
                    value={projecaoAtiva ?? ""}
                    titulo={projecaoAtiva ?? undefined}
                    opcoes={resumoAtivo.projections.map((id) => ({
                      value: id,
                      rotulo: ROTULO_PROJECAO[id] ?? id,
                      id: ROTULO_PROJECAO[id] ? id : undefined,
                    }))}
                    onChange={(id) => setProjecaoAtiva(id)}
                  />
                </Campo>
              )}
            </section>

            <section className="cartao" data-tour="x-comunidades">
              <Passo
                n={3}
                titulo="Comunidades"
                ajuda="Definem a cor e a forma."
              />
              {particoes.length === 0 ? (
                <p className="nota">nenhuma partição desta projeção em disco</p>
              ) : (
                <Campo id={null}>
                  <Seletor
                    nome="Algoritmo de comunidades"
                    value={particaoAtiva ?? ""}
                    titulo={particaoAtiva ?? undefined}
                    opcoes={[
                      { value: "", rotulo: "sem cor por comunidade" },
                      ...particoes.map((id) => {
                        const algoritmo = id.split("__")[0];
                        return { value: id, rotulo: ROTULO_ALGORITMO[algoritmo] ?? algoritmo };
                      }),
                    ]}
                    onChange={(id) => setParticaoAtiva(id || null)}
                  />
                </Campo>
              )}
              {particao && membership && (
                <>
                  <div className="q-metrica">
                    <b><i>Q</i> = {particao.modularity.toLocaleString("pt-BR", { minimumFractionDigits: 4, maximumFractionDigits: 4 })}</b>
                    <span>modularidade</span>
                    {particao.status !== "ok" && <span>{particao.status}</span>}
                  </div>
                  <CommunityLegend membership={membership} info={leitura?.communities}
                    foco={foco} onFoco={setFoco}
                    desfecho={mostrarDesfecho ? desfechos : null} sinais={leitura?.signals?.by_community} />
                  {mostrarDesfecho && desfechos && <LegendaDeDesfecho rotulos={desfechos.labels} />}
                </>
              )}
            </section>

            {membership && (
              <section className="cartao" data-tour="x-leitura">
                <Passo n={4} titulo="Leitura" ajuda="O que este grafo diz." />
                {leitura ? (
                  <>
                    <ul className="lab-resumo campo">
                      {leitura.summary.map((frase) => <li key={frase}>{frase}</li>)}
                    </ul>
                    <ul className="papeis campo">
                      {PAPEIS.map((p) => (
                        <li key={p}>
                          <button type="button" className={`papel-filtro papel-${p}`} aria-pressed={papel === p}
                            disabled={leitura.role_counts[p] === 0} title={leitura.role_help[p]}
                            onClick={() => {
                              setPapel(papel === p ? null : p);
                              setSinal(null);
                            }}>
                            <span className="papel-selo">{leitura.role_labels[p]}</span>
                            <span className="papel-n">{leitura.role_counts[p]}</span>
                          </button>
                        </li>
                      ))}
                    </ul>
                    {papel && <p className="opcoes-desc">{leitura.role_help[papel]}</p>}
                    <PainelSinais
                      leitura={leitura}
                      rotulo={(id) => rotulosDosNos.get(id) ?? id}
                      grupoDe={(id) => nomesDasComunidades[membership?.[id] ?? -1]}
                      filtro={sinal}
                      onFiltro={(f) => {
                        setSinal(f);
                        if (f) setPapel(null);
                      }}
                      onSelecionar={setSelecionado}
                    />
                  </>
                ) : (
                  <p className="nota nota-carregando">lendo o resultado…</p>
                )}
                {dadosGrafo && dadosGrafo.nodes.length <= 300 && (
                  <label className="opcao campo">
                    <input type="checkbox" checked={bolhas} onChange={(e) => setBolhas(e.target.checked)} />
                    Contornos das comunidades
                  </label>
                )}
                {desfechos && (
                  <>
                    <label className="opcao campo">
                      <input type="checkbox" checked={mostrarDesfecho} onChange={(e) => setMostrarDesfecho(e.target.checked)} />
                      Revelar o desfecho (aprovado, reprovado…)
                    </label>
                    {mostrarDesfecho && (
                      <p className="opcoes-desc">O grafo não usou notas nem desfecho; eles só foram cruzados com os grupos agora.</p>
                    )}
                    {mostrarDesfecho && desfechos?.signals && (
                      <div className="campo">
                        <Conferencia validacao={desfechos.signals} />
                      </div>
                    )}
                  </>
                )}
              </section>
            )}

            <section className="cartao">
              <Passo
                n={5}
                titulo="Centralidade"
                ajuda="Define o tamanho dos nós."
              />
              {dadosGrafo && metricasDisponiveis.length === 0 ? (
                <p className="nota">
                  sem centralidades desta projeção em disco
                  <br />
                  <code>python -m edugraph centrality all</code>
                </p>
              ) : (
                <div className="segmentado" role="radiogroup" aria-label="Métrica de tamanho">
                  {[{ id: null, nome: "Igual" }, ...metricasDisponiveis].map((m) => (
                    <button
                      key={m.id ?? "nenhuma"}
                      type="button"
                      role="radio"
                      aria-checked={metricaAtiva === m.id}
                      className={metricaAtiva === m.id ? "ativo" : ""}
                      onClick={() => setMetricaAtiva(m.id as CentralityMetric | null)}
                    >
                      <span className="radio-marca" aria-hidden="true" />
                      {m.nome}
                    </button>
                  ))}
                </div>
              )}
              <p className="opcoes-desc">{DESCRICAO_METRICA[metricaAtiva ?? "igual"]}</p>
            </section>
          </>
        )}

      </aside>
      </>
      )}

      <footer className="rodape">
        <span>Repositório do TCC: <a href={URL_REPOSITORIO} target="_blank" rel="noopener noreferrer"
          aria-label="Repositório do TCC no GitHub (abre em nova aba)">luctmc/TCC.bipartite-network-analysis</a></span>
        <span>TCC · Grupo 16 · UniAnchieta</span>
      </footer>
      {tour && <Tour key={tour} passos={PASSOS[tour]} onFechar={() => fecharTour(tour)} />}
    </div>
    </MotionConfig>
  );
}

const URL_REPOSITORIO = "https://github.com/luctmc/TCC.bipartite-network-analysis";

/** Autores do trabalho (os mesmos de `pyproject.toml`). */
const AUTORES = [
  "Gabriel Luís Lopes",
  "Pedro Alexandre dos Santos Chaves",
  "Lucas Timponi Mercadante Castro",
];

/**
 * Rótulos de exibição. O `value` das opções e o id que vai para a API continuam
 * sendo o id técnico; o id aparece abaixo do seletor, em fonte monoespaçada.
 */
const ROTULO_PROJECAO: Record<string, string> = {
  discipline_resource_allocation: "Disciplinas · alocação de recursos",
  discipline_simple: "Disciplinas · projeção simples",
  student_resource_allocation: "Alunos · alocação de recursos",
  student_simple: "Alunos · projeção simples",
};
const ROTULO_ALGORITMO: Record<string, string> = {
  louvain: "Louvain",
  girvan_newman: "Girvan–Newman",
};

function Passo(props: { n: number; titulo: string; ajuda: string }) {
  return (
    <header className="passo">
      <span className="passo-num" aria-hidden="true">
        {props.n}
      </span>
      <div className="passo-texto">
        <h2>{props.titulo}</h2>
        <p>{props.ajuda}</p>
      </div>
    </header>
  );
}

/** Espaço do seletor, com o id técnico (secundário) logo abaixo quando há. */
function Campo(props: { id: string | null; children: React.ReactNode }) {
  return (
    <div className="campo">
      {props.children}
      {props.id && <code className="campo-id">{props.id}</code>}
    </div>
  );
}

function Marca() {
  return <svg viewBox="0 0 32 16" width="32" height="16" aria-hidden="true">
    <circle cx="5" cy="8" r="4.5" fill="#56B4E9" />
    <path d="M16 3 21 12.5H11Z" fill="#E69F00" />
    <rect x="23" y="3.5" width="8.5" height="8.5" rx="2" fill="#009E73" />
  </svg>;
}

const DESCRICAO_METRICA: Record<string, string> = {
  igual: "Igual: todos os nós têm o mesmo tamanho.",
  degree: "Grau: quantos vizinhos o nó tem.",
  betweenness: "Intermediação: quanto o nó faz ponte entre grupos.",
  eigenvector: "Autovetor: quanto os vizinhos do nó também são centrais.",
};

function BotaoTema({ tema, onAlternar }: { tema: Tema; onAlternar: () => void }) {
  const claro = tema === "light";
  return (
    <button
      type="button"
      className="tema-botao"
      aria-pressed={claro}
      aria-label="Alternar tema claro e escuro"
      title={claro ? "Usar o modo escuro" : "Usar o modo claro"}
      onClick={onAlternar}
    >
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        {claro ? (
          <>
            <circle cx="12" cy="12" r="4" />
            <path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4" />
          </>
        ) : (
          <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z" />
        )}
      </svg>
      Tema
    </button>
  );
}

function StatusApi({ estado }: { estado: Estado<HealthResponse> }) {
  if (estado.status !== "pronto") {
    return (
      <span className="status-pilula status-off">
        <span className="status-ponto" aria-hidden="true" />
        API offline
      </span>
    );
  }
  return (
    <div className="status-pilula">
      <span className="status-ponto" aria-hidden="true" />
      <span className="status-versao">API v{estado.dados.version}</span>
      <span
        className="status-raizes"
        tabIndex={0}
        title={`Raízes de artefatos consultadas, em ordem: ${estado.dados.roots.join(" · ")}`}
      >
        {estado.dados.roots.join(" · ")}
      </span>
    </div>
  );
}

function Vazio({ children, tipo }: {
  children: React.ReactNode;
  tipo: "vazio" | "carregando" | "erro";
}) {
  return <div className={`vazio vazio-${tipo}`} role={tipo === "erro" ? "alert" : "status"}
    aria-live={tipo === "erro" ? undefined : "polite"}>
    <h2>{tipo === "vazio" ? "Nenhuma figura ainda" : tipo === "carregando" ? "Carregando a projeção…" : "A API não respondeu"}</h2>
    <p>{children}</p>
    {tipo === "carregando" && <span className="fio" aria-hidden="true"><span /></span>}
  </div>;
}
