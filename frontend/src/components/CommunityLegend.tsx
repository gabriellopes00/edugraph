/**
 * Legenda das comunidades — spec C-05 e ADR-0013.
 *
 * Mostra cor **e** forma de cada comunidade, com o tamanho: em escala de
 * cinza é a forma que identifica o grupo (ver `palette.ts`). Com a
 * leitura do resultado (`/insight`), cada comunidade ganha **nome** e
 * uma linha de descrição; passar o mouse (ou o foco do teclado) destaca
 * o grupo no grafo, e clicar o fixa. Com o desfecho (`/outcomes`), cada
 * linha ganha uma barra com aprovados, reprovados e desistentes — a
 * revelação a posteriori, que o grafo nunca viu.
 */

import { communityOrder, communityStyle } from "../palette";
import type { CommunityInfo, OutcomeRow, Sinais } from "../types";

/** Comunidades listadas antes do "e mais N" — as menores costumam ser unitárias. */
const MAX_ITENS = 10;

/** Silhueta em SVG da forma do Cytoscape, para a legenda. */
export const SILHUETAS: Record<string, string> = {
  ellipse: "M8 1a7 7 0 1 0 0.01 0Z",
  triangle: "M8 1 15 15H1Z",
  "round-rectangle": "M3 2h10a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Z",
  diamond: "M8 0 16 8 8 16 0 8Z",
  hexagon: "M4 1h8l4 7-4 7H4L0 8Z",
  star: "M8 0l2.4 5.2 5.6.6-4.2 3.8 1.2 5.6L8 12.4 3 15.2l1.2-5.6L0 5.8l5.6-.6Z",
  vee: "M0 1 8 6 16 1 8 15Z",
  pentagon: "M8 0 16 6 13 15H3L0 6Z",
};

/** Ordem e cor de cada desfecho na barra; a cor nunca é o único sinal (há o texto). */
const DESFECHOS: { id: string; cor: string }[] = [
  { id: "Distinction", cor: "#0072B2" },
  { id: "Pass", cor: "#56B4E9" },
  { id: "Fail", cor: "#D55E00" },
  { id: "Withdrawn", cor: "#E69F00" },
];

const pct = (v: number) => `${Math.round(100 * v)}%`;

interface Props {
  membership: Record<string, number>;
  /** Nome e descrição por comunidade, quando a leitura já chegou. */
  info?: CommunityInfo[];
  foco?: number | null;
  onFoco?: (comunidade: number | null) => void;
  desfecho?: { rows: OutcomeRow[]; labels: Record<string, string> } | null;
  /** Contagem de alunos em risco e talentos por comunidade. */
  sinais?: Sinais["by_community"] | null;
}

export function CommunityLegend({ membership, info, foco = null, onFoco, desfecho, sinais }: Props) {
  const ordem = communityOrder(membership);
  const tamanhos = new Map<number, number>();
  for (const comunidade of Object.values(membership)) {
    tamanhos.set(comunidade, (tamanhos.get(comunidade) ?? 0) + 1);
  }
  const itens = [...ordem.entries()].sort((a, b) => a[1] - b[1]);
  const total = Object.keys(membership).length;
  const dados = new Map(info?.map((c) => [c.id, c]));
  const linhas = new Map(desfecho?.rows.map((r) => [r.community, r]));

  return (
    <ul className="legenda" onMouseLeave={() => onFoco?.(null)}>
      {itens.slice(0, MAX_ITENS).map(([comunidade, posicao]) => {
        const { color, shape } = communityStyle(posicao);
        const n = tamanhos.get(comunidade) ?? 0;
        const sobre = dados.get(comunidade);
        const nome = sobre?.name ?? `Comunidade ${comunidade}`;
        const desfechoDoGrupo = linhas.get(comunidade);
        return (
          <li
            key={comunidade}
            className={foco === comunidade ? "em-foco" : foco !== null ? "fora-de-foco" : ""}
          >
            <button
              type="button"
              className="legenda-item"
              aria-pressed={foco === comunidade}
              onMouseEnter={() => onFoco?.(comunidade)}
              onFocus={() => onFoco?.(comunidade)}
              onBlur={() => onFoco?.(null)}
              onClick={() => onFoco?.(foco === comunidade ? null : comunidade)}
              title={sobre?.description ?? nome}
            >
              <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
                <path d={SILHUETAS[shape] ?? SILHUETAS.ellipse} fill={color} stroke="var(--node-stroke)" strokeWidth="1" />
              </svg>
              <span className="legenda-nome">{nome}</span>
              <span className="legenda-num">{n} {n === 1 ? "nó" : "nós"}</span>
              <span className="legenda-pct">{((100 * n) / total).toFixed(0)}%</span>
            </button>
            {sobre && <p className="legenda-desc">{sobre.description}</p>}
            <ResumoDeSinais linha={sinais?.[String(comunidade)]} />
            {desfechoDoGrupo && desfechoDoGrupo.n_labeled > 0 && desfecho && (
              <BarraDeDesfecho linha={desfechoDoGrupo} rotulos={desfecho.labels} />
            )}
          </li>
        );
      })}
      {itens.length > MAX_ITENS && (
        <li className="legenda-resto dim">e mais {itens.length - MAX_ITENS} comunidades menores</li>
      )}
    </ul>
  );
}

/** "3 em risco · 2 em atenção · 4 talentos" de um grupo; nada, se não há sinal. */
function ResumoDeSinais({ linha }: { linha?: { alto: number; atencao: number; talentos: number } }) {
  if (!linha || linha.alto + linha.atencao + linha.talentos === 0) return null;
  const partes: string[] = [];
  if (linha.alto) partes.push(`${linha.alto} em risco`);
  if (linha.atencao) partes.push(`${linha.atencao} em atenção`);
  if (linha.talentos) partes.push(`${linha.talentos} ${linha.talentos === 1 ? "talento" : "talentos"}`);
  return <p className="legenda-sinais">{partes.join(" · ")}</p>;
}

/** Barra empilhada do desfecho do grupo, com o texto de cada fatia. */
export function BarraDeDesfecho({ linha, rotulos }: { linha: OutcomeRow; rotulos: Record<string, string> }) {
  const resumo = DESFECHOS.map(({ id }) => `${rotulos[id] ?? id}: ${pct(linha.rates[id] ?? 0)}`).join(" · ");
  return (
    <div className="desfecho" role="img" aria-label={resumo} title={resumo}>
      <div className="desfecho-barra">
        {DESFECHOS.map(({ id, cor }) => (
          <span key={id} style={{ width: `${100 * (linha.rates[id] ?? 0)}%`, background: cor }} />
        ))}
      </div>
      <p className="desfecho-texto">
        {pct((linha.rates.Fail ?? 0) + (linha.rates.Withdrawn ?? 0))} reprovados ou desistentes ·{" "}
        {pct((linha.rates.Pass ?? 0) + (linha.rates.Distinction ?? 0))} aprovados
      </p>
    </div>
  );
}

/** Legenda da barra de desfecho. */
export function LegendaDeDesfecho({ rotulos }: { rotulos: Record<string, string> }) {
  return (
    <ul className="desfecho-legenda">
      {DESFECHOS.map(({ id, cor }) => (
        <li key={id}>
          <span style={{ background: cor }} aria-hidden="true" />
          {rotulos[id] ?? id}
        </li>
      ))}
    </ul>
  );
}
