/**
 * Cliente da API.
 *
 * A API é somente leitura (ADR-0004): não há POST, não há cálculo sob
 * demanda. Todo endpoint aqui é um GET sobre artefato já em disco.
 *
 * `ApiError.notFound` distingue o artefato ausente (404, a mensagem cita
 * as raízes consultadas) de um erro de verdade; `notImplemented` (501)
 * sobra para rotas cuja spec ainda esteja aberta.
 */

import type {
  CentralityMetric,
  CentralityResponse,
  DatasetListResponse,
  GraphResponse,
  HealthResponse,
  InsightResponse,
  LabOptions,
  LabRequest,
  LabRun,
  OutcomesResponse,
  PartitionResponse,
} from "./types";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }

  /** 501: a rota existe, mas a spec que a implementa ainda está aberta. */
  get notImplemented(): boolean {
    return this.status === 501;
  }

  /** 404: dataset, projeção ou partição inexistente sob as raízes da API. */
  get notFound(): boolean {
    return this.status === 404;
  }
}

function errorDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (!Array.isArray(detail)) return fallback;
  const messages = detail.flatMap((entry: unknown) => {
    if (typeof entry !== "object" || entry === null || !("msg" in entry)) return [];
    if (typeof entry.msg !== "string" || !entry.msg.trim()) return [];
    const loc = "loc" in entry && Array.isArray(entry.loc)
      ? entry.loc.filter((part: unknown) => typeof part === "string" || typeof part === "number").join(".")
      : "";
    return [loc ? `${loc}: ${entry.msg}` : entry.msg];
  });
  return messages.join("; ") || fallback;
}

async function send<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { Accept: "application/json", ...(init.headers as Record<string, string>) },
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: unknown };
      detail = errorDetail(body.detail, response.statusText);
    } catch {
      // resposta sem corpo JSON: fica o statusText mesmo
    }
    throw new ApiError(response.status, detail);
  }

  return (await response.json()) as T;
}

const get = <T>(path: string) => send<T>(path);

const post = <T>(path: string, body: unknown) =>
  send<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const api = {
  health: () => get<HealthResponse>("/health"),

  datasets: () => get<DatasetListResponse>("/datasets"),

  /**
   * Grafo de uma projeção. `partition` e `metrics` pedem que a partição
   * e as centralidades venham embutidas, evitando uma segunda ida ao
   * servidor só para colorir e dimensionar.
   */
  projection: (
    dataset: string,
    projectionId: string,
    options: { partition?: string; metrics?: CentralityMetric[] } = {},
  ) => {
    const params = new URLSearchParams();
    if (options.partition) params.set("partition", options.partition);
    if (options.metrics?.length) params.set("metrics", options.metrics.join(","));
    const query = params.toString();

    return get<GraphResponse>(
      `/datasets/${encodeURIComponent(dataset)}/projections/` +
        `${encodeURIComponent(projectionId)}${query ? `?${query}` : ""}`,
    );
  },

  partition: (dataset: string, artifactId: string) =>
    get<PartitionResponse>(
      `/datasets/${encodeURIComponent(dataset)}/communities/${encodeURIComponent(artifactId)}`,
    ),

  /** Nome das comunidades, papel dos nós e frases-resumo de uma partição em disco. */
  insight: (dataset: string, artifactId: string) =>
    get<InsightResponse>(
      `/datasets/${encodeURIComponent(dataset)}/communities/${encodeURIComponent(artifactId)}/insight`,
    ),

  /** Desfecho por comunidade — a revelação a posteriori (ADR-0008). */
  outcomes: (dataset: string, artifactId: string) =>
    get<OutcomesResponse>(
      `/datasets/${encodeURIComponent(dataset)}/communities/${encodeURIComponent(artifactId)}/outcomes`,
    ),

  /** Fontes e limites do laboratório. */
  labOptions: () => get<LabOptions>("/lab/options"),

  /** Monta a rede na hora, com o algoritmo de verdade, e devolve o passo a passo. */
  labRun: (request: Partial<LabRequest>) => post<LabRun>("/lab/run", request),

  /** Ranking de uma métrica. `top` limita às N primeiras posições. */
  centrality: (dataset: string, projectionId: string, metric: CentralityMetric, top?: number) =>
    get<CentralityResponse>(
      `/datasets/${encodeURIComponent(dataset)}/centrality/` +
        `${encodeURIComponent(projectionId)}/${metric}${top ? `?top=${top}` : ""}`,
    ),

  /**
   * Quais das três métricas existem em disco para a projeção. Consulta
   * cada uma com `top=1` (leitura barata) para que o grafo, que é a
   * requisição cara, seja pedido uma vez só e com as métricas certas.
   */
  availableMetrics: async (
    dataset: string,
    projectionId: string,
    metrics: CentralityMetric[],
  ): Promise<CentralityMetric[]> => {
    const found = await Promise.all(
      metrics.map((metric) =>
        api
          .centrality(dataset, projectionId, metric, 1)
          .then(() => metric)
          // Só 404 quer dizer "não calculada"; qualquer outro erro (API fora,
          // 500) sobe, em vez de se passar por métrica ausente.
          .catch((erro: unknown) => {
            if (erro instanceof ApiError && erro.notFound) return null;
            throw erro;
          }),
      ),
    );
    return found.filter((metric): metric is CentralityMetric => metric !== null);
  },
};
