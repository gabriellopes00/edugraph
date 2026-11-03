/**
 * Painel do nó selecionado — spec C-05.
 *
 * Comunidade, as três centralidades (com a posição no ranking) e os
 * vizinhos, do mais forte para o mais fraco. Clicar num vizinho o
 * seleciona, o que permite percorrer o grafo pelo painel durante a
 * apresentação.
 */

import { type CSSProperties } from "react";
import { motion } from "framer-motion";

import { communityOrder, communityStyle, themeColor } from "../palette";
import { SILHUETAS } from "./CommunityLegend";
import type { CentralityMetric, GraphResponse, Insight, RoleId, SinalDoAluno, Sinais } from "../types";

const METRICAS: { id: CentralityMetric; nome: string }[] = [
  { id: "degree", nome: "Grau" },
  { id: "betweenness", nome: "Intermediação" },
  { id: "eigenvector", nome: "Autovetor" },
];

/** Vizinhos mostrados antes do "e mais N". */
const MAX_VIZINHOS = 12;

interface NodePanelProps {
  graph: GraphResponse;
  membership: Record<string, number> | null;
  nodeId: string;
  onSelect: (nodeId: string | null) => void;
  /** Leitura do resultado: dá nome à comunidade e papel ao nó. */
  leitura?: Insight | null;
}

/**
 * Ordem por ponto de código, a mesma do `sorted` do Python — `localeCompare`
 * ordena por idioma e, num empate, daria uma posição diferente da API.
 */
function porCodigo(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

/** Posição do nó no ranking da métrica (1 = maior), com o mesmo desempate por id da API. */
function posicao(scores: Record<string, number>, nodeId: string): number {
  const ordenados = Object.entries(scores).sort((a, b) => b[1] - a[1] || porCodigo(a[0], b[0]));
  return ordenados.findIndex(([id]) => id === nodeId) + 1;
}

export function NodePanel({ graph, membership, nodeId, onSelect, leitura }: NodePanelProps) {
  const no = graph.nodes.find((node) => node.id === nodeId);
  if (!no) return null;

  const rotulos = new Map(graph.nodes.map((node) => [node.id, node.label]));
  const vizinhos = graph.edges
    .filter((edge) => edge.source === nodeId || edge.target === nodeId)
    .map((edge) => ({
      id: edge.source === nodeId ? edge.target : edge.source,
      weight: edge.weight,
    }))
    .sort((a, b) => b.weight - a.weight || porCodigo(a.id, b.id));

  const pesoMax = vizinhos[0]?.weight ?? 0;

  const ordem = membership ? communityOrder(membership) : null;
  const estiloDe = (id: string) => {
    const c = membership?.[id];
    return ordem && c !== undefined ? communityStyle(ordem.get(c) ?? 0) : null;
  };
  const comunidade = membership?.[nodeId];
  const estiloComunidade = estiloDe(nodeId);
  const nomeDaComunidade = leitura?.communities.find((c) => c.id === comunidade)?.name;
  const papel = leitura?.roles[nodeId];
  const sinal = leitura?.signals?.students[nodeId];
  // Sem partição, o nó usa a cor e a forma do tipo (aluno / disciplina), como no grafo.
  const disciplina = no.kind === "discipline";
  const corNo =
    estiloComunidade?.color ??
    themeColor(disciplina ? "--node-discipline" : "--node-student", disciplina ? "#f0a868" : "#6ea8fe");
  const formaNo = estiloComunidade?.shape ?? (disciplina ? "round-rectangle" : "ellipse");

  return (
    <motion.section
      className="node-panel"
      key={nodeId}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
    >
      <header className="node-panel-topo">
        <span>{disciplina ? "Disciplina" : "Aluno"}</span>
        <button type="button" className="fechar" onClick={() => onSelect(null)} aria-label="Fechar painel do nó">
          <svg viewBox="0 0 14 14" width="13" height="13" aria-hidden="true"><path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" strokeWidth="1.5" /></svg>
        </button>
      </header>
      <h2 className="node-panel-nome">{no.label}</h2>
      <p className="comunidade-chip">
        <Silhueta forma={formaNo} cor={corNo} tamanho={15} />
        {estiloComunidade ? <>{nomeDaComunidade ?? `Comunidade ${comunidade}`} · {Object.values(membership ?? {}).filter(c => c === comunidade).length} de {graph.nodes.length} nós</> : "sem comunidade"}
      </p>
      {papel && leitura && <PapelDoNo papel={papel.role} leitura={leitura} />}
      {sinal && leitura?.signals && <SinaisDoAluno sinal={sinal} sinais={leitura.signals} />}
      <h3>Centralidade <span>posição entre {graph.nodes.length}</span></h3>
      <div className="metricas">
        {METRICAS.map(({ id, nome }) => {
          const scores = graph.centrality?.[id];
          const valor = scores?.[nodeId];
          return (
            <Metrica
              key={id}
              nome={nome}
              valor={valor}
              posicao={scores && valor !== undefined ? posicao(scores, nodeId) : null}
              total={scores ? Object.keys(scores).length : 0}
            />
          );
        })}
      </div>

      <div className="vizinhos-bloco">
        <h3>
          Vizinhos <span>{vizinhos.length}, por peso</span>
        </h3>
        {graph.truncation.truncated && (
          <p className="dim">Só entre as arestas mostradas (a resposta foi cortada).</p>
        )}
        <ul className="vizinhos">
          {vizinhos.slice(0, MAX_VIZINHOS).map((vizinho) => {
            const nome = rotulos.get(vizinho.id) ?? vizinho.id;
            const estiloVizinho = estiloDe(vizinho.id);
            return (
              <li key={vizinho.id}>
                <button
                  type="button"
                  onClick={() => onSelect(vizinho.id)}
                  title={nome}
                  style={{ "--w": `${pesoMax > 0 ? (100 * vizinho.weight) / pesoMax : 0}%` } as CSSProperties}
                >
                  <span className="vizinho-forma">
                    {estiloVizinho && (
                      <Silhueta forma={estiloVizinho.shape} cor={estiloVizinho.color} tamanho={12} />
                    )}
                  </span>
                  <span className="vizinho-nome">{nome}</span>
                  <span className="vizinho-peso">{vizinho.weight.toLocaleString("pt-BR")}</span>
                  <span className="vizinho-barra" aria-hidden="true"><span /></span>
                </button>
              </li>
            );
          })}
        </ul>
        {vizinhos.length > MAX_VIZINHOS && (
          <p className="dim resto">e mais {vizinhos.length - MAX_VIZINHOS}</p>
        )}
      </div>
    </motion.section>
  );
}

/** Forma chapada com contorno contrastante, igual ao grafo. */
function Silhueta(props: { forma: string; cor: string; tamanho: number }) {
  return <svg className="amostra" viewBox="0 0 16 16" width={props.tamanho} height={props.tamanho} aria-hidden="true">
    <path d={SILHUETAS[props.forma] ?? SILHUETAS.ellipse} fill={props.cor} stroke="var(--node-stroke)" strokeWidth="1" strokeLinejoin="round" />
  </svg>;
}

/** Posição exata em texto; até 15 pontos, proporcionais em redes maiores. */
function Metrica(props: { nome: string; valor: number | undefined; posicao: number | null; total: number }) {
  const { nome, valor, posicao: pos, total } = props;
  const marcas = Math.min(total, 15);
  const marca = pos === null ? -1 : total <= 15 ? pos - 1 : Math.round((pos - 1) * (marcas - 1) / (total - 1));
  return <div className="metrica">
    <span className="metrica-nome">{nome}</span>
    <span className={`metrica-valor ${valor === undefined ? "metrica-nula" : ""}`}>
      {valor === undefined ? "não calculada" : valor.toLocaleString("pt-BR", { minimumFractionDigits: 4, maximumFractionDigits: 4 })}
    </span>
    {valor !== undefined && pos !== null && <div className="metrica-ranking">
      <span className="pontos" role="img" aria-label={`${pos}º lugar entre ${total} nós`}>
        {Array.from({ length: marcas }, (_, i) => <i key={i} className={i === marca ? "on" : ""} />)}
      </span>
      <span className="posicao"><b>{pos}º</b> de {total}</span>
    </div>}
  </div>;
}

/** O papel do nó na rede, com o que ele quer dizer. */
function PapelDoNo({ papel, leitura }: { papel: RoleId; leitura: Insight }) {
  return (
    <div className={`papel papel-${papel}`}>
      <span className="papel-selo">{leitura.role_labels[papel]}</span>
      <span className="papel-ajuda">{leitura.role_help[papel]}</span>
    </div>
  );
}

/** Risco de evasão e selos de talento do aluno, com o porquê de cada um. */
function SinaisDoAluno({ sinal, sinais }: { sinal: SinalDoAluno; sinais: Sinais }) {
  const rotulo = sinal.talent ? "Possível talento" : sinais.tier_labels[sinal.tier];
  return (
    <div className={`sinal-aluno sinal-${sinal.talent ? "talento" : sinal.tier}`}>
      <div className="sinal-aluno-topo">
        <span className="papel-selo">{rotulo}</span>
        <span className="sinal-risco-valor">risco {Math.round(100 * sinal.risk)}%</span>
      </div>
      <div className="sinal-risco-barra" role="img" aria-label={`Risco de evasão: ${Math.round(100 * sinal.risk)}%`}>
        <span style={{ width: `${100 * sinal.risk}%` }} />
      </div>
      {sinal.tags && sinal.tags.length > 0 && (
        <p className="aluno-tags">
          {sinal.tags.map((t) => (
            <span key={t} className="aluno-tag">{sinais.tag_labels[t] ?? t}</span>
          ))}
        </p>
      )}
      {sinal.why && sinal.why.length > 0 && (
        <ul className="aluno-porques">
          {sinal.why.map((f) => <li key={f}>{f}</li>)}
        </ul>
      )}
    </div>
  );
}
