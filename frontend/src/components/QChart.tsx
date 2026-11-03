/**
 * Gráfico de Q ao vivo — ADR-0013.
 *
 * Louvain: Q depois de cada movimento (cresce até o resultado).
 * Girvan–Newman: Q de cada corte, pelo número de grupos; o pico é o
 * melhor corte, e o algoritmo devolve aquele.
 *
 * Linha em SVG, sem biblioteca. A referência em 0,3 é a regra prática
 * de Newman (2004) para "grupos bem definidos".
 */

import { useId } from "react";

import type { SerieQ } from "../lab/frames";

const LARGURA = 300;
const ALTURA = 132;
const MARGEM = { esq: 34, dir: 10, topo: 10, base: 24 };

const fmt = (n: number) => n.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

export function QChart({ serie, atual }: { serie: SerieQ; atual: number }) {
  const id = useId();
  const { pontos, melhor, eixoX } = serie;
  if (pontos.length === 0) return null;

  const xs = pontos.map((p) => p.x);
  const ys = pontos.map((p) => p.y);
  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs);
  const yMin = Math.min(-0.05, ...ys);
  const yMax = Math.max(0.6, ...ys);
  const x = (v: number) => MARGEM.esq + ((v - xMin) / Math.max(xMax - xMin, 1)) * (LARGURA - MARGEM.esq - MARGEM.dir);
  const y = (v: number) => MARGEM.topo + (1 - (v - yMin) / (yMax - yMin)) * (ALTURA - MARGEM.topo - MARGEM.base);
  const caminho = (lista: typeof pontos) => lista.map((p, i) => `${i === 0 ? "M" : "L"}${x(p.x).toFixed(1)} ${y(p.y).toFixed(1)}`).join(" ");

  // Louvain cresce até o ponto atual; Girvan–Newman mostra a curva inteira.
  const curvaInteira = eixoX === "grupos";
  const feito = curvaInteira ? pontos : pontos.slice(0, Math.max(atual + 1, 1));
  const marcador = atual >= 0 && atual < pontos.length ? pontos[atual] : null;
  const pico = melhor !== null ? pontos[melhor] : null;
  const ticksY = [0, 0.3, 0.6].filter((t) => t >= yMin && t <= yMax);

  return (
    <figure className="qchart">
      <svg
        viewBox={`0 0 ${LARGURA} ${ALTURA}`}
        role="img"
        aria-label={`Modularidade Q por ${eixoX === "grupos" ? "número de grupos" : "movimento"}`}
      >
        <title id={id}>Modularidade Q ao longo do algoritmo</title>
        {ticksY.map((t) => (
          <g key={t}>
            <line className={t === 0.3 ? "qchart-ref" : "qchart-eixo"} x1={MARGEM.esq} x2={LARGURA - MARGEM.dir} y1={y(t)} y2={y(t)} />
            <text className="qchart-texto" x={MARGEM.esq - 6} y={y(t)} textAnchor="end" dominantBaseline="middle">{fmt(t)}</text>
          </g>
        ))}
        {!curvaInteira && <path className="qchart-fantasma" d={caminho(pontos)} />}
        <path className="qchart-linha" d={caminho(feito)} />
        {curvaInteira && pontos.map((p, i) => (
          <circle key={i} className="qchart-ponto" cx={x(p.x)} cy={y(p.y)} r={i === melhor ? 0 : 2} />
        ))}
        {pico && (
          <g>
            <circle className="qchart-pico" cx={x(pico.x)} cy={y(pico.y)} r="5.5" />
            <text className="qchart-texto qchart-destaque" x={x(pico.x) + 9} y={y(pico.y) - 7}>
              melhor corte
            </text>
          </g>
        )}
        {marcador && <circle className="qchart-atual" cx={x(marcador.x)} cy={y(marcador.y)} r="4" />}
        <text className="qchart-texto" x={MARGEM.esq} y={ALTURA - 5}>{eixoX === "grupos" ? `${xMin} grupos` : "início"}</text>
        <text className="qchart-texto" x={LARGURA - MARGEM.dir} y={ALTURA - 5} textAnchor="end">
          {eixoX === "grupos" ? `${xMax} grupos` : `${xMax} movimentos`}
        </text>
        <text className="qchart-texto qchart-titulo" x={4} y={9}>Q</text>
      </svg>
    </figure>
  );
}
