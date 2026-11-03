/**
 * Espelho dos schemas pydantic de `edugraph/api/schemas.py`.
 *
 * Mudar um schema lá é mudar o contrato com o front: sai em PR com os
 * dois lados juntos. Para conferir se ainda batem:
 *
 *     python -m edugraph api openapi > /tmp/openapi.json
 */

export type NodeKind = "student" | "discipline";
export type CentralityMetric = "degree" | "betweenness" | "eigenvector";
export type RunStatus = "ok" | "timeout" | "skipped";

export interface HealthResponse {
  status: "ok";
  version: string;
  schema_version: string;
  /** Raízes de artefatos que a API está consultando, em ordem. */
  roots: string[];
}

export interface DatasetSummary {
  dataset: string;
  has_bipartite: boolean;
  projections: string[];
  /** Ids no formato `<algoritmo>__<projection_id>`. */
  partitions: string[];
  centralities: string[];
}

export interface DatasetListResponse {
  datasets: DatasetSummary[];
}

export interface GraphNode {
  id: string;
  kind: NodeKind;
  label: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  weight: number;
}

/**
 * O corte de arestas da resposta. Quando `truncated`, a API manteve todos
 * os nós e escolheu as arestas por `criterion`: `backbone` (as
 * `k_per_node` mais fortes de cada nó) ou `top_weight` (as mais pesadas
 * do grafo inteiro).
 */
export interface TruncationInfo {
  truncated: boolean;
  max_edges: number;
  n_nodes: number;
  n_edges_total: number;
  n_edges_returned: number;
  criterion: "backbone" | "top_weight";
  /** No `backbone`: arestas por nó que couberam; 0 = nem uma por nó coube. */
  k_per_node: number | null;
}

export interface GraphResponse {
  dataset: string;
  projection_id: string;
  spec: Record<string, unknown>;
  nodes: GraphNode[];
  edges: GraphEdge[];
  truncation: TruncationInfo;
  /** Nó → comunidade, quando a partição foi pedida junto. */
  community?: Record<string, number> | null;
  /** Métrica → (nó → score), quando as centralidades foram pedidas junto. */
  centrality?: Record<string, Record<string, number>> | null;
}

export interface PartitionResponse {
  dataset: string;
  algorithm: string;
  projection_id: string;
  modularity: number;
  n_communities: number;
  runtime_s: number;
  status: RunStatus;
  params: Record<string, unknown>;
  membership: Record<string, number>;
}

export interface CentralityResponse {
  dataset: string;
  projection_id: string;
  metric: CentralityMetric;
  converged: boolean;
  runtime_s: number;
  params: Record<string, unknown>;
  /** Pares [nó, score], já ordenados do maior para o menor. */
  ranking: [string, number][];
}

export interface MetricsResponse {
  dataset: string;
  name: string;
  /** Linhas de `metrics/<name>.csv`; números já convertidos. */
  rows: Record<string, string | number>[];
}

// ---------------------------------------------------------------------
// Leitura dos resultados e laboratório (ADR-0013)
// ---------------------------------------------------------------------

export type RoleId = "referencia" | "conector" | "ponte" | "periferico";

export interface CommunityInfo {
  id: number;
  /** Nome pelas disciplinas que o grupo reúne, ou pelo nível de engajamento. */
  name: string;
  size: number;
  share: number;
  description: string;
  /** Itens que definem o grupo (disciplinas acima da média da turma). */
  top: { label: string; share: number; lift: number }[];
}

export interface RoleInfo {
  role: RoleId;
  /** Grau dentro do próprio grupo, em desvios-padrão. */
  z: number;
  /** Coeficiente de participação: 0 = só liga dentro do grupo. */
  p: number;
}

export type PerfilId = "risco" | "atencao" | "talento" | "referencia" | "ponte" | "regular";
export type Faixa = "alto" | "atencao" | "baixo";

/** Sinais de um aluno, calculados só com o grafo (ver `edugraph.lab.signals`). */
export interface SinalDoAluno {
  /** Risco de evasão, de 0 a 1. */
  risk: number;
  tier: Faixa;
  profile: PerfilId;
  talent: boolean;
  /** Ordena os talentos: quanto maior, mais destacado. */
  strength: number;
  /** Selos de talento (chaves de `tag_labels`). */
  tags?: string[];
  /** Por que foi sinalizado, em frases. */
  why?: string[];
}

export interface Sinais {
  students: Record<string, SinalDoAluno>;
  counts: { alto: number; atencao: number; talentos: number; total: number };
  profile_counts: Record<PerfilId, number>;
  profile_labels: Record<PerfilId, string>;
  profile_help: Record<PerfilId, string>;
  tier_labels: Record<Faixa, string>;
  tag_labels: Record<string, string>;
  /** Alunos em atenção, do maior risco ao menor. */
  attention: string[];
  /** Possíveis talentos, do mais destacado ao menos. */
  talents: string[];
  by_community: Record<string, { n: number; alto: number; atencao: number; talentos: number }>;
  /** O que a intensidade mede: notas ou atividade. */
  performance: "notas" | "atividade";
  flat_intensity: boolean;
}

/** Bloco de desfechos de um grupo de alunos. */
export interface BlocoDeDesfecho {
  n: number;
  n_labeled: number;
  counts: Record<string, number>;
  rates: Record<string, number>;
}

/** Os sinais conferidos contra o desfecho real (a revelação a posteriori). */
export interface ValidacaoDosSinais {
  risk: { base: BlocoDeDesfecho; groups: Record<string, BlocoDeDesfecho> };
  talent: { base: BlocoDeDesfecho; groups: Record<string, BlocoDeDesfecho> };
  auc_negative: number | null;
  auc_withdrawn: number | null;
}

export interface Insight {
  communities: CommunityInfo[];
  roles: Record<string, RoleInfo>;
  role_counts: Record<RoleId, number>;
  role_labels: Record<RoleId, string>;
  role_help: Record<RoleId, string>;
  /** Frases-resumo, geradas por regra a partir da partição. */
  summary: string[];
  /** Risco de evasão e talentos; `null` quando os nós são disciplinas. */
  signals?: Sinais | null;
}

export interface InsightResponse extends Insight {
  dataset: string;
  artifact_id: string;
}

export interface OutcomeRow {
  community: number;
  size: number;
  n_labeled: number;
  rates: Record<string, number>;
  base_rates: Record<string, number>;
  counts: Record<string, number>;
}

export interface OutcomesResponse {
  dataset: string;
  artifact_id: string;
  /** Desfecho técnico → texto ("Fail" → "Reprovados"). */
  labels: Record<string, string>;
  /** Vazio quando o dataset não tem rótulos. */
  rows: OutcomeRow[];
  signals?: ValidacaoDosSinais | null;
}

export interface LabRequest {
  source: string;
  students: number;
  seed: number;
  noise: number;
  side: NodeKind;
  weighting: "simple" | "resource_allocation";
  algorithm: "louvain" | "girvan_newman";
  min_weight: number | null;
  time_budget_s: number;
}

export interface LabSource {
  id: string;
  title: string;
  fictional: boolean;
}

export interface LabOptions {
  sources: LabSource[];
  min_students: number;
  max_students: number;
  max_edges_girvan_newman: number;
  areas: { name: string; disciplines: string[] }[];
}

export interface LabBipartite {
  students: { id: string; label: string }[];
  disciplines: { id: string; label: string }[];
  /** [aluno, disciplina, nota média] */
  edges: [string, string, number][];
}

export interface LabProjection {
  side: NodeKind;
  weighting: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  /** Menor e maior peso antes do corte de ligações fracas. */
  weight_range: [number, number];
  /** Corte que mantém ~30% das ligações mais fortes, para redes quase completas. */
  suggested_min_weight: number | null;
  min_weight: number | null;
  n_edges_before_cut: number;
}

/** Um movimento do Louvain: estes nós (índices em `nodes`) vão para a comunidade `to`. */
export interface LouvainMove {
  members: number[];
  to: number;
  q: number;
  level: number;
}

export interface LouvainTrace {
  nodes: string[];
  moves: LouvainMove[];
  levels: { level: number; n_moves: number; q: number; n_communities: number }[];
  reference: { library: string; q: number; n_communities: number; same_partition: boolean };
}

export interface GirvanNewmanSplit {
  k: number;
  q: number;
  /** Quantas arestas já tinham sido removidas quando este corte apareceu. */
  n_removed: number;
  membership: Record<string, number> | null;
}

export interface GirvanNewmanTrace {
  nodes: string[];
  /** Arestas removidas, na ordem, como pares de índices em `nodes`. */
  removed: [number, number][];
  splits: GirvanNewmanSplit[];
  /** Índice, em `splits`, do corte de maior Q; -1 se não houve corte. */
  best: number;
  stop_reason: string;
}

export interface LabResult {
  membership: Record<string, number>;
  q: number;
  n_communities: number;
  runtime_s: number;
  status: RunStatus;
  stop_reason: string | null;
}

export interface LabReveal {
  planted?: {
    areas: { name: string; disciplines: string[] }[];
    node_area: Record<string, string>;
    nmi: number;
    purity: number;
  };
  outcomes?: { rows: OutcomeRow[]; labels: Record<string, string> };
  signals?: ValidacaoDosSinais;
}

export interface LabRun {
  request: LabRequest;
  source: LabSource;
  bipartite: LabBipartite;
  projection: LabProjection;
  louvain: LouvainTrace | null;
  girvan_newman: GirvanNewmanTrace | null;
  result: LabResult;
  insight: Insight;
  centrality: Record<string, Record<string, number>>;
  reveal: LabReveal;
  timing: { total_s: number };
}
