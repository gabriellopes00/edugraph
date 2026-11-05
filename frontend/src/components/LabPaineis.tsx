/**
 * Painéis laterais do laboratório — ADR-0013.
 *
 * Durante a animação, a coluna da direita narra a etapa em português
 * corrido e mostra os números ao vivo. No fim, ela vira a leitura do
 * resultado: frases-resumo, comunidades com nome, papéis dos nós, e as
 * duas revelações — as áreas que o gerador plantou e o desfecho dos
 * alunos —, que o grafo nunca viu.
 */

import type { ReactNode } from "react";

import { pontoAtual, serieQ, type Estado } from "../lab/frames";
import type { CentralityMetric, LabRun, RoleId } from "../types";
import { CommunityLegend, LegendaDeDesfecho } from "./CommunityLegend";
import { QChart } from "./QChart";
import { Conferencia, PainelSinais, type SinalFiltro } from "./Sinais";

export const NOME_ALGORITMO: Record<string, string> = {
  louvain: "Louvain",
  girvan_newman: "Girvan–Newman",
};

const decimal = (n: number, casas = 2) =>
  n.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });

const segundos = (s: number) => (s < 0.01 ? "menos de 0,01 s" : `${decimal(s, s < 1 ? 2 : 1)} s`);

export function Numero({ rotulo, valor }: { rotulo: string; valor: ReactNode }) {
  return (
    <div className="numero">
      <dt>{rotulo}</dt>
      <dd>{valor}</dd>
    </div>
  );
}

// ---------------------------------------------------------------------
// Durante a animação
// ---------------------------------------------------------------------

function textoDaEtapa(run: LabRun, estado: Estado): { titulo: string; corpo: ReactNode } {
  const { students, disciplines, edges } = {
    students: run.bipartite.students.length,
    disciplines: run.bipartite.disciplines.length,
    edges: run.bipartite.edges.length,
  };
  const alunos = run.projection.side === "student";
  const ponderacao =
    run.projection.weighting === "resource_allocation" ? (
      <>
        <b>Alocação de recursos:</b> cada disciplina em comum vale 1 dividido pelo número de alunos
        nela — uma disciplina concorrida liga menos do que uma de poucos alunos.
      </>
    ) : (
      <>
        <b>Projeção simples:</b> o peso da ligação é quantas disciplinas os dois têm em comum.
      </>
    );

  switch (estado.etapa) {
    case "matriculas":
      return {
        titulo: "1 · Matrículas",
        corpo: (
          <>
            <p>
              São <b>{students}</b> alunos e <b>{disciplines}</b> disciplinas. Cada linha liga um
              aluno a uma disciplina que ele cursou
              {run.source.fictional ? " com nota média de pelo menos 50" : ""}: {edges} matrículas
              ao todo.
            </p>
            <p className="dim">
              É o grafo <b>bipartido</b>: dois tipos de nó, e só há ligação entre tipos diferentes.
              Assim, ninguém aparece ligado a outro aluno — ainda.
            </p>
          </>
        ),
      };
    case "projecao":
      return {
        titulo: "2 · Projeção",
        corpo: (
          <>
            <p>
              {alunos
                ? "Os dois tipos de nó viram um só. Dois alunos se ligam quando cursam a mesma disciplina; quanto mais disciplinas em comum, mais grossa a linha."
                : "Os dois tipos de nó viram um só. Duas disciplinas se ligam quando têm alunos em comum; quanto mais alunos, mais grossa a linha."}
            </p>
            <p className="dim">{ponderacao}</p>
          </>
        ),
      };
    case "algoritmo":
      return run.louvain
        ? {
            titulo: "3 · Louvain",
            corpo: (
              <>
                <p>
                  No começo, cada {alunos ? "aluno" : "disciplina"} é um grupo só dele. Um a um, cada
                  nó vai para o grupo vizinho que mais aumenta a <b>modularidade Q</b> — uma nota de
                  quão separados estão os grupos.
                </p>
                <p className="dim">Quando ninguém quer mais trocar, o algoritmo termina.</p>
              </>
            ),
          }
        : {
            titulo: "3 · Girvan–Newman",
            corpo: (
              <>
                <p>
                  A cada passo, o algoritmo apaga a ligação mais usada como <b>ponte</b> entre
                  grupos (a de maior intermediação, em vermelho). Quando a rede se parte, nasce um
                  grupo.
                </p>
                <p className="dim">
                  Ele guarda o corte de maior Q. É lento porque recalcula as pontes depois de cada
                  ligação apagada.
                </p>
              </>
            ),
          };
    default:
      return { titulo: "4 · Resultado", corpo: null };
  }
}

export function PainelEtapa({ run, estado }: { run: LabRun; estado: Estado }) {
  const { titulo, corpo } = textoDaEtapa(run, estado);
  const noAlgoritmo = estado.etapa === "algoritmo";
  const serie = serieQ(run);
  const rotuloPasso = run.louvain ? "Movimentos" : "Ligações removidas";
  return (
    <section className="lab-etapa" aria-live="polite">
      <h2>{titulo}</h2>
      <div className="lab-texto">{corpo}</div>
      {noAlgoritmo && (
        <>
          <dl className="numeros">
            <Numero rotulo={rotuloPasso} valor={`${estado.passo} / ${estado.total}`} />
            <Numero rotulo="Grupos" valor={estado.k ?? "—"} />
            <Numero rotulo="Q agora" valor={estado.q === null ? "—" : decimal(estado.q, 3)} />
          </dl>
          <QChart serie={serie} atual={pontoAtual(run, estado)} />
          <p className="dim lab-nota">
            {run.louvain
              ? "Q sobe a cada movimento. Acima de 0,3, os grupos já são bem definidos."
              : "A curva mostra o Q de cada corte; o pico é o melhor. Depois dele, cortar mais só piora."}
          </p>
        </>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------
// Depois: a leitura do resultado
// ---------------------------------------------------------------------

const PAPEIS: RoleId[] = ["referencia", "conector", "ponte", "periferico"];

export interface ComparacaoItem {
  algoritmo: string;
  q: number;
  grupos: number;
  segundos: number;
  status: string;
}

interface PainelResultadoProps {
  run: LabRun;
  foco: number | null;
  onFoco: (c: number | null) => void;
  papel: RoleId | null;
  onPapel: (p: RoleId | null) => void;
  metrica: CentralityMetric | null;
  metricas: { id: CentralityMetric; nome: string }[];
  onMetrica: (m: CentralityMetric | null) => void;
  bolhas: boolean;
  onBolhas: (v: boolean) => void;
  plantadas: boolean;
  onPlantadas: (v: boolean) => void;
  desfecho: boolean;
  onDesfecho: (v: boolean) => void;
  comparacao: ComparacaoItem[];
  sinal: SinalFiltro | null;
  onSinal: (f: SinalFiltro | null) => void;
  onSelecionar: (id: string) => void;
  /** Mostra o convite para o tour do resultado (só até o visitante responder). */
  convite: boolean;
  onEntender: () => void;
  onDispensarConvite: () => void;
}

export function PainelResultado(p: PainelResultadoProps) {
  const { run } = p;
  const { insight, result, reveal } = run;
  const planted = reveal.planted;
  const lib = run.louvain?.reference;
  const rotulos = Object.fromEntries(run.projection.nodes.map((n) => [n.id, n.label]));
  const nomesDosGrupos = Object.fromEntries(insight.communities.map((c) => [c.id, c.name]));

  return (
    <section className="lab-resultado">
      {p.convite && (
        <aside className="lab-convite" aria-label="Convite para o tour do resultado">
          <p>
            <b>Primeira vez aqui?</b> Veja em 4 passos como ler este resultado.
          </p>
          <button type="button" className="convite-principal" onClick={p.onEntender}>
            Mostrar
          </button>
          <button type="button" onClick={p.onDispensarConvite}>
            Agora não
          </button>
        </aside>
      )}
      <header className="lab-resultado-topo">
        <h2>4 · Resultado</h2>
        <button type="button" className="botao-entender" onClick={p.onEntender}>
          Entender o resultado
        </button>
        <p className="dim">
          {NOME_ALGORITMO[run.request.algorithm]} · calculado agora em {segundos(result.runtime_s)}
          {result.status !== "ok" && <> · <b>{result.status === "timeout" ? "parou por tempo" : result.status}</b></>}
        </p>
      </header>

      <ul className="lab-resumo" data-tour="resumo">
        {insight.summary.map((frase) => (
          <li key={frase}>{frase}</li>
        ))}
      </ul>

      <div data-tour="grupos">
        <h3>Os grupos <span>passe o mouse para destacar</span></h3>
        <CommunityLegend
          membership={result.membership}
          info={insight.communities}
          foco={p.foco}
          onFoco={p.onFoco}
          desfecho={p.desfecho && reveal.outcomes ? reveal.outcomes : null}
          sinais={insight.signals?.by_community}
        />
        {p.desfecho && reveal.outcomes && <LegendaDeDesfecho rotulos={reveal.outcomes.labels} />}
      </div>

      {insight.signals && (
        <PainelSinais
          leitura={insight}
          rotulo={(id) => rotulos[id] ?? id}
          grupoDe={(id) => nomesDosGrupos[run.result.membership[id]]}
          filtro={p.sinal}
          onFiltro={p.onSinal}
          onSelecionar={p.onSelecionar}
        />
      )}

      <h3>Papel de cada nó <span>clique para filtrar</span></h3>
      <ul className="papeis">
        {PAPEIS.map((papel) => (
          <li key={papel}>
            <button
              type="button"
              className={`papel-filtro papel-${papel}`}
              aria-pressed={p.papel === papel}
              disabled={insight.role_counts[papel] === 0}
              onClick={() => p.onPapel(p.papel === papel ? null : papel)}
              title={insight.role_help[papel]}
            >
              <span className="papel-selo">{insight.role_labels[papel]}</span>
              <span className="papel-n">{insight.role_counts[papel]}</span>
            </button>
          </li>
        ))}
      </ul>
      {p.papel && <p className="dim lab-nota">{insight.role_help[p.papel]}</p>}

      <h3>Como ver</h3>
      <div className="segmentado" role="radiogroup" aria-label="Tamanho dos nós">
        {[{ id: null, nome: "Igual" }, ...p.metricas].map((m) => (
          <button
            key={m.id ?? "nenhuma"}
            type="button"
            role="radio"
            aria-checked={p.metrica === m.id}
            className={p.metrica === m.id ? "ativo" : ""}
            onClick={() => p.onMetrica(m.id as CentralityMetric | null)}
          >
            <span className="radio-marca" aria-hidden="true" />
            {m.nome}
          </button>
        ))}
      </div>
      <label className="opcao">
        <input type="checkbox" checked={p.bolhas} onChange={(e) => p.onBolhas(e.target.checked)} />
        Contornos das comunidades
      </label>

      {(planted || reveal.outcomes) && (
        <div data-tour="revelar">
          <h3>Revelar <span>o que o grafo nunca viu</span></h3>
          {planted && (
            <label className="opcao">
              <input type="checkbox" checked={p.plantadas} onChange={(e) => p.onPlantadas(e.target.checked)} />
              As áreas que o gerador plantou
            </label>
          )}
          {planted && p.plantadas && (
            <p className="lab-nota">
              A turma foi sorteada com {planted.areas.length} áreas (
              {planted.areas.map((a) => a.name).join(", ")}). O algoritmo não sabia disso e acertou a
              área de <b>{Math.round(100 * planted.purity)}%</b> dos {run.projection.side === "student" ? "alunos" : "nós"}{" "}
              (pureza; NMI = {decimal(planted.nmi)}). Os contornos tracejados são as áreas
              verdadeiras.
            </p>
          )}
          {reveal.outcomes && (
            <label className="opcao">
              <input type="checkbox" checked={p.desfecho} onChange={(e) => p.onDesfecho(e.target.checked)} />
              O desfecho dos alunos (aprovado, reprovado…)
            </label>
          )}
          {p.desfecho && reveal.outcomes && (
            <p className="lab-nota dim">
              O grafo foi montado sem olhar notas nem desfecho; eles só foram cruzados com os grupos
              agora.{run.source.fictional ? " Aqui o desfecho é sintético: o gerador sorteia alguns alunos \"em risco\", com notas menores e mais abandono." : ""}
            </p>
          )}
          {p.desfecho && reveal.signals && <Conferencia validacao={reveal.signals} ficticio={run.source.fictional} />}
        </div>
      )}

      {lib && (
        <>
          <h3>Conferência</h3>
          <p className="lab-nota">
            O Louvain desta tela foi escrito para mostrar cada movimento. A biblioteca{" "}
            <code>{lib.library}</code> acha Q = <b>{decimal(lib.q, 3)}</b> e {lib.n_communities} grupos;
            o nosso acha Q = <b>{decimal(result.q, 3)}</b> e {result.n_communities}.{" "}
            {lib.same_partition ? "A partição é a mesma." : "As partições diferem em alguns nós."}
          </p>
        </>
      )}

      {p.comparacao.length > 1 && (
        <>
          <h3>Mesma turma, os dois algoritmos</h3>
          <table className="lab-tabela">
            <thead>
              <tr><th>Algoritmo</th><th>Q</th><th>Grupos</th><th>Tempo</th></tr>
            </thead>
            <tbody>
              {p.comparacao.map((c) => (
                <tr key={c.algoritmo} className={c.algoritmo === run.request.algorithm ? "atual" : ""}>
                  <td>{NOME_ALGORITMO[c.algoritmo]}</td>
                  <td>{decimal(c.q, 3)}</td>
                  <td>{c.grupos}</td>
                  <td>{segundos(c.segundos)}{c.status !== "ok" ? " *" : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}
