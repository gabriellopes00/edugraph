/**
 * Perfis dos alunos: risco de evasão e possíveis talentos — ADR-0013.
 *
 * Os sinais vêm do backend (`edugraph.lab.signals`) e são calculados só
 * com o grafo: nenhuma nota ou desfecho entra na conta. Esta peça mostra
 * a distribuição dos perfis, lista quem merece atenção e quem se
 * destaca (cada um com o porquê, em frase), e — quando o desfecho é
 * revelado — confere os sinais contra o que aconteceu de fato.
 */

import { useMemo, useState, type ReactNode } from "react";

import type { BlocoDeDesfecho, Insight, PerfilId, Sinais, ValidacaoDosSinais } from "../types";

/** Qual grupo de alunos fica em destaque no grafo. */
export type SinalFiltro = "risco" | "atencao" | "talento";

/** Cor de cada perfil. A cor nunca está sozinha: há sempre o texto ao lado. */
const COR_PERFIL: Record<PerfilId, string> = {
  risco: "#D55E00",
  atencao: "#E69F00",
  talento: "#009E73",
  referencia: "#56B4E9",
  ponte: "#CC79A7",
  regular: "var(--rule-control)",
};

const ORDEM_PERFIS: PerfilId[] = ["risco", "atencao", "talento", "referencia", "ponte", "regular"];

const FILTROS: { id: SinalFiltro; perfil: PerfilId }[] = [
  { id: "risco", perfil: "risco" },
  { id: "atencao", perfil: "atencao" },
  { id: "talento", perfil: "talento" },
];

/** Quantos cartões a lista de um filtro mostra de cada vez; o resto vem por "Mostrar mais". */
const POR_PAGINA = 40;

const pct = (v: number) => `${Math.round(100 * v)}%`;
const decimal = (n: number, casas = 2) =>
  n.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });

/** Ids dos alunos de um filtro, para o grafo destacar. */
export function idsDoSinal(sinais: Sinais | null | undefined, filtro: SinalFiltro | null): Set<string> | null {
  if (!sinais || !filtro) return null;
  const ids = new Set<string>();
  for (const [id, s] of Object.entries(sinais.students)) {
    if (filtro === "risco" ? s.tier === "alto" : filtro === "atencao" ? s.tier === "atencao" : s.talent) ids.add(id);
  }
  return ids;
}

interface Props {
  leitura: Insight;
  /** Nome do aluno a partir do id do nó. */
  rotulo: (id: string) => string;
  /** Nome da comunidade de um aluno, para situá-lo. */
  grupoDe: (id: string) => string | undefined;
  filtro: SinalFiltro | null;
  onFiltro: (f: SinalFiltro | null) => void;
  onSelecionar: (id: string) => void;
}

export function PainelSinais({ leitura, rotulo, grupoDe, filtro, onFiltro, onSelecionar }: Props) {
  const sinais = leitura.signals;
  if (!sinais) return null;
  const { counts } = sinais;

  return (
    <div className="sinais" data-tour="perfis">
      <h3>
        Perfis dos alunos <span>clique para filtrar</span>
      </h3>
      <BarraDePerfis sinais={sinais} />
      <ul className="papeis sinais-filtros">
        {FILTROS.map(({ id, perfil }) => {
          const n = id === "risco" ? counts.alto : id === "atencao" ? counts.atencao : counts.talentos;
          return (
            <li key={id}>
              <button
                type="button"
                className="papel-filtro"
                aria-pressed={filtro === id}
                disabled={n === 0}
                onClick={() => onFiltro(filtro === id ? null : id)}
                title={sinais.profile_help[perfil]}
              >
                <span className="sinal-ponto" style={{ background: COR_PERFIL[perfil] }} aria-hidden="true" />
                <span className="papel-selo">{sinais.profile_labels[perfil]}</span>
                <span className="papel-n">{n}</span>
              </button>
            </li>
          );
        })}
      </ul>
      {filtro && <p className="lab-nota dim">{sinais.profile_help[filtro]}</p>}
      <p className="lab-nota dim">
        São <b>indicadores estruturais</b>, não previsões: dizem quem, no grafo, se parece com quem se afasta
        ou se destaca. Usam só as matrículas e os grupos; nenhuma nota nem desfecho entrou na conta.
      </p>

      {filtro && (
        <ListaDoFiltro
          key={filtro}
          filtro={filtro}
          sinais={sinais}
          rotulo={rotulo}
          grupoDe={grupoDe}
          onSelecionar={onSelecionar}
        />
      )}

      {!filtro && sinais.attention.length > 0 && (
        <>
          <h3>
            Quem merece atenção <span>{counts.alto + counts.atencao} no total</span>
          </h3>
          <ul className="alunos-lista">
            {sinais.attention.map((id) => (
              <CartaoDoAluno key={id} id={id} sinais={sinais} rotulo={rotulo} grupo={grupoDe(id)} onSelecionar={onSelecionar} />
            ))}
          </ul>
          {counts.alto + counts.atencao > sinais.attention.length && (
            <p className="lab-nota dim">
              Mostrando os {sinais.attention.length} de maior risco; use o filtro para ver todos.
            </p>
          )}
        </>
      )}

      {!filtro && sinais.talents.length > 0 && (
        <>
          <h3>
            Possíveis talentos <span>{counts.talentos} no total</span>
          </h3>
          <ul className="alunos-lista">
            {sinais.talents.map((id) => (
              <CartaoDoAluno key={id} id={id} sinais={sinais} rotulo={rotulo} grupo={grupoDe(id)} onSelecionar={onSelecionar} />
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

/**
 * Todos os alunos de um filtro, e não só os primeiros do resumo: o backend manda
 * `attention` e `talents` cortados, mas `students` traz cada aluno com o porquê.
 * Mesma ordem do resumo: maior risco primeiro; talentos, do mais destacado.
 */
function ListaDoFiltro({
  filtro,
  sinais,
  rotulo,
  grupoDe,
  onSelecionar,
}: {
  filtro: SinalFiltro;
  sinais: Sinais;
  rotulo: (id: string) => string;
  grupoDe: (id: string) => string | undefined;
  onSelecionar: (id: string) => void;
}) {
  const [visiveis, setVisiveis] = useState(POR_PAGINA);
  const ids = useMemo(() => {
    const nota = (id: string) => (filtro === "talento" ? -sinais.students[id].strength : -sinais.students[id].risk);
    return [...(idsDoSinal(sinais, filtro) ?? [])].sort(
      (a, b) => nota(a) - nota(b) || (rotulo(a) < rotulo(b) ? -1 : rotulo(a) > rotulo(b) ? 1 : a < b ? -1 : 1),
    );
  }, [sinais, filtro, rotulo]);
  const perfil = FILTROS.find((f) => f.id === filtro)?.perfil ?? "risco";
  return (
    <>
      <h3>
        {sinais.profile_labels[perfil]} <span>{ids.length} no total</span>
      </h3>
      <ul className="alunos-lista">
        {ids.slice(0, visiveis).map((id) => (
          <CartaoDoAluno key={id} id={id} sinais={sinais} rotulo={rotulo} grupo={grupoDe(id)} onSelecionar={onSelecionar} />
        ))}
      </ul>
      {ids.length > visiveis && (
        <button type="button" className="botao-secundario" onClick={() => setVisiveis((v) => v + POR_PAGINA)}>
          Mostrar mais ({ids.length - visiveis} restantes)
        </button>
      )}
    </>
  );
}

function BarraDePerfis({ sinais }: { sinais: Sinais }) {
  const total = sinais.counts.total || 1;
  const resumo = ORDEM_PERFIS.map((p) => `${sinais.profile_labels[p]}: ${sinais.profile_counts[p]}`).join(" · ");
  return (
    <div className="perfis-barra" role="img" aria-label={resumo} title={resumo}>
      {ORDEM_PERFIS.map((p) =>
        sinais.profile_counts[p] > 0 ? (
          <span key={p} style={{ width: `${(100 * sinais.profile_counts[p]) / total}%`, background: COR_PERFIL[p] }} />
        ) : null,
      )}
    </div>
  );
}

function CartaoDoAluno({
  id,
  sinais,
  rotulo,
  grupo,
  onSelecionar,
}: {
  id: string;
  sinais: Sinais;
  rotulo: (id: string) => string;
  grupo?: string;
  onSelecionar: (id: string) => void;
}) {
  const s = sinais.students[id];
  if (!s) return null;
  const talento = s.talent;
  const perfil: PerfilId = talento ? "talento" : s.tier === "alto" ? "risco" : "atencao";
  return (
    <li className="aluno-cartao">
      <button type="button" onClick={() => onSelecionar(id)} title="Ver este aluno no grafo">
        <span className="aluno-topo">
          <span className="sinal-ponto" style={{ background: COR_PERFIL[perfil] }} aria-hidden="true" />
          <span className="aluno-nome">{rotulo(id)}</span>
          <span className="aluno-selo">
            {talento ? "Talento" : sinais.tier_labels[s.tier]}
            {!talento && ` · ${Math.round(100 * s.risk)}%`}
          </span>
        </span>
        {grupo && <span className="aluno-grupo">{grupo}</span>}
        {talento && s.tags && (
          <span className="aluno-tags">
            {s.tags.map((t) => (
              <span key={t} className="aluno-tag">
                {sinais.tag_labels[t] ?? t}
              </span>
            ))}
          </span>
        )}
        <ul className="aluno-porques">
          {(s.why ?? []).map((frase) => (
            <li key={frase}>{frase}</li>
          ))}
        </ul>
      </button>
    </li>
  );
}

// ---------------------------------------------------------------------
// Conferência com o desfecho real
// ---------------------------------------------------------------------

function negativos(b: BlocoDeDesfecho): number {
  return (b.rates.Fail ?? 0) + (b.rates.Withdrawn ?? 0);
}

function positivos(b: BlocoDeDesfecho): number {
  return (b.rates.Pass ?? 0) + (b.rates.Distinction ?? 0);
}

/**
 * Os sinais conferidos contra o desfecho real. Fica junto da opção que revela o
 * desfecho (quem a liga vê a tabela ali, sem rolar), e não entre os perfis.
 */
export function Conferencia({ validacao, ficticio }: { validacao: ValidacaoDosSinais; ficticio?: boolean }) {
  const { risk, talent } = validacao;
  const alto = risk.groups.alto;
  const atencao = risk.groups.atencao;
  const baixo = risk.groups.baixo;
  const talentos = talent.groups.talento;
  const demais = talent.groups.demais;
  const linhas: { nome: string; bloco: BlocoDeDesfecho | undefined }[] = [
    { nome: "Risco alto", bloco: alto },
    { nome: "Em atenção", bloco: atencao },
    { nome: "Sem sinais", bloco: baixo },
    { nome: "Turma toda", bloco: risk.base },
  ];
  const celula = (b: BlocoDeDesfecho | undefined, f: (b: BlocoDeDesfecho) => number) =>
    b && b.n_labeled > 0 ? pct(f(b)) : "—";

  const frases: ReactNode[] = [];
  if (alto && alto.n_labeled > 0 && baixo && baixo.n_labeled > 0) {
    frases.push(
      <>
        Entre os <b>{alto.n_labeled}</b> alunos de risco alto, <b>{pct(negativos(alto))}</b> reprovaram ou
        desistiram — contra <b>{pct(negativos(baixo))}</b> dos alunos sem sinais e {pct(negativos(risk.base))} da
        turma toda.
      </>,
    );
  }
  if (talentos && talentos.n_labeled > 0 && demais && demais.n_labeled > 0) {
    frases.push(
      <>
        Dos <b>{talentos.n_labeled}</b> possíveis talentos, <b>{pct(positivos(talentos))}</b> foram aprovados
        (<b>{pct(talentos.rates.Distinction ?? 0)}</b> com distinção), contra {pct(positivos(demais))} dos demais.
      </>,
    );
  }

  return (
    <section className="conferencia">
      <h3>
        Conferindo com o que aconteceu <span>o grafo nunca viu isto</span>
      </h3>
      <table className="lab-tabela">
        <thead>
          <tr>
            <th>Grupo</th>
            <th>Alunos</th>
            <th>Reprovaram ou desistiram</th>
            <th>Desistiram</th>
          </tr>
        </thead>
        <tbody>
          {linhas.map(({ nome, bloco }) => (
            <tr key={nome} className={nome === "Turma toda" ? "atual" : ""}>
              <td>{nome}</td>
              <td>{bloco?.n_labeled ?? 0}</td>
              <td>{celula(bloco, negativos)}</td>
              <td>{celula(bloco, (b) => b.rates.Withdrawn ?? 0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {frases.map((f, i) => (
        <p key={i} className="lab-nota">
          {f}
        </p>
      ))}
      {validacao.auc_negative !== null && (
        <p className="lab-nota dim">
          Ordenando todos os alunos pelo risco, a chance de quem reprovou ou desistiu ficar à frente de quem não
          (AUC) é <b>{decimal(validacao.auc_negative)}</b>; 0,50 seria acaso e 1,00, separação perfeita.
          {ficticio
            ? " A turma é fictícia: o gerador sorteia alunos em risco com notas menores e mais abandono, e o resultado muda de turma para turma."
            : ""}
        </p>
      )}
    </section>
  );
}
