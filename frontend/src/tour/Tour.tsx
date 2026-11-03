/**
 * Tour de boas-vindas — ADR-0013.
 *
 * Escurece a tela, deixa acesa só a área do passo e explica num balão ao
 * lado. Sem biblioteca: o recorte é uma sombra enorme em volta de um
 * retângulo, que segue o elemento quando a janela muda de tamanho ou algo
 * rola. Teclado: ← → trocam de passo, Esc fecha, Tab fica preso no balão.
 * No celular o balão vira uma folha presa ao pé da tela.
 */

import {
  Fragment,
  useCallback,
  useEffect,
  useId,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";

import { passosVisiveis, posicionarBalao, type Posicao } from "./estado";
import type { Passo } from "./passos";

/** Abaixo disto o balão vira folha no pé da tela. */
const LARGURA_CELULAR = 700;
const LARGURA_BALAO = 350;
/** Respiro entre o contorno e o elemento destacado. */
const RESPIRO = 7;

/** `**negrito**` dentro de um parágrafo. */
function Texto({ texto }: { texto: string }): ReactNode {
  return texto.split("**").map((trecho, i) =>
    i % 2 === 1 ? <b key={i}>{trecho}</b> : <Fragment key={i}>{trecho}</Fragment>,
  );
}

interface Props {
  passos: Passo[];
  /** `concluiu` é falso quando o visitante pulou ou fechou antes do fim. */
  onFechar: (concluiu: boolean) => void;
}

export function Tour({ passos, onFechar }: Props) {
  // Os passos com alvo ausente (ex.: a revelação num dataset sem rótulos) saem
  // da lista na abertura, e não no meio do caminho.
  const lista = useMemo(
    () => passosVisiveis(passos, (seletor) => document.querySelector(seletor) !== null),
    [passos],
  );
  const [indice, setIndice] = useState(0);
  const [alvo, setAlvo] = useState<DOMRect | null>(null);
  const [posicao, setPosicao] = useState<Posicao | null>(null);
  const [celular, setCelular] = useState(() => window.innerWidth < LARGURA_CELULAR);
  const balaoRef = useRef<HTMLDivElement>(null);
  const principalRef = useRef<HTMLButtonElement>(null);
  const titulo = useId();

  const passo = lista[Math.min(indice, lista.length - 1)];
  const ultimo = indice >= lista.length - 1;

  const avancar = useCallback(() => {
    if (ultimo) onFechar(true);
    else setIndice((i) => i + 1);
  }, [ultimo, onFechar]);
  const voltar = useCallback(() => setIndice((i) => Math.max(0, i - 1)), []);

  // Mede o alvo do passo e o acompanha quando a tela muda ou algo rola.
  useLayoutEffect(() => {
    if (!passo) return;
    const elemento = passo.alvo ? document.querySelector<HTMLElement>(passo.alvo) : null;
    elemento?.scrollIntoView({ block: window.innerWidth < LARGURA_CELULAR ? "center" : "nearest", inline: "nearest" });
    const medir = () => {
      setCelular(window.innerWidth < LARGURA_CELULAR);
      setAlvo(elemento ? elemento.getBoundingClientRect() : null);
    };
    medir();
    // Uma segunda medida depois da rolagem, que o navegador faz no quadro seguinte.
    const quadro = window.requestAnimationFrame(medir);
    window.addEventListener("resize", medir);
    window.addEventListener("scroll", medir, true);
    const observador = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(medir);
    if (elemento) observador?.observe(elemento);
    return () => {
      window.cancelAnimationFrame(quadro);
      window.removeEventListener("resize", medir);
      window.removeEventListener("scroll", medir, true);
      observador?.disconnect();
    };
  }, [passo]);

  // Posiciona o balão depois de saber o tamanho dele e o do alvo.
  useLayoutEffect(() => {
    const balao = balaoRef.current;
    if (!balao || !passo) return;
    setPosicao(
      posicionarBalao(
        alvo && { left: alvo.left, top: alvo.top, width: alvo.width, height: alvo.height },
        { w: balao.offsetWidth, h: balao.offsetHeight },
        { w: window.innerWidth, h: window.innerHeight },
        passo.lado,
      ),
    );
  }, [alvo, passo, indice]);

  // O foco vai para o botão principal a cada passo, e volta ao que estava ao fechar.
  useEffect(() => {
    principalRef.current?.focus({ preventScroll: true });
  }, [indice]);
  useEffect(() => {
    const anterior = document.activeElement as HTMLElement | null;
    return () => anterior?.focus?.({ preventScroll: true });
  }, []);

  // Teclado. Em fase de captura, para o resto da página (F, espaço, setas do
  // laboratório) não reagir enquanto o tour está aberto.
  useEffect(() => {
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key === "Tab") {
        const focaveis = balaoRef.current?.querySelectorAll<HTMLElement>("button:not(:disabled)");
        if (!focaveis?.length) return;
        const primeiro = focaveis[0];
        const final = focaveis[focaveis.length - 1];
        if (e.shiftKey && document.activeElement === primeiro) {
          e.preventDefault();
          final.focus();
        } else if (!e.shiftKey && document.activeElement === final) {
          e.preventDefault();
          primeiro.focus();
        }
        return;
      }
      e.stopPropagation();
      if (e.key === "Escape") {
        e.preventDefault();
        onFechar(false);
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        avancar();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        voltar();
      }
    };
    window.addEventListener("keydown", aoTeclar, true);
    return () => window.removeEventListener("keydown", aoTeclar, true);
  }, [avancar, voltar, onFechar]);

  if (!passo) return null;

  const luz: CSSProperties | undefined = alvo
    ? {
        left: alvo.left - RESPIRO,
        top: alvo.top - RESPIRO,
        width: alvo.width + 2 * RESPIRO,
        height: alvo.height + 2 * RESPIRO,
      }
    : undefined;
  const estiloBalao: CSSProperties | undefined = celular
    ? undefined
    : { left: posicao?.left ?? 0, top: posicao?.top ?? 0, width: LARGURA_BALAO, visibility: posicao ? "visible" : "hidden" };
  const abertura = !passo.alvo;

  return (
    <div className="tour" data-lado={posicao?.lado}>
      <div className={`tour-fundo ${luz ? "" : "escuro"}`} aria-hidden="true" />
      {luz && <div className={`tour-luz ${passo.pulsar ? "pulsa" : ""}`} style={luz} aria-hidden="true" />}
      <div
        ref={balaoRef}
        className={`tour-balao ${celular ? "folha" : ""} ${abertura ? "abertura" : ""}`}
        style={estiloBalao}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titulo}
      >
        <p className="tour-progresso">
          {abertura && indice === 0 ? "Tour" : `${indice + 1} de ${lista.length}`}
          <span className="tour-pontos" aria-hidden="true">
            {lista.map((_, i) => (
              <i key={i} className={i === indice ? "atual" : i < indice ? "feito" : ""} />
            ))}
          </span>
        </p>
        <h2 id={titulo}>{passo.titulo}</h2>
        {passo.corpo.map((paragrafo) => (
          <p key={paragrafo} className="tour-texto">
            <Texto texto={paragrafo} />
          </p>
        ))}
        <div className="tour-acoes">
          {indice > 0 ? (
            <button type="button" className="tour-secundario" onClick={voltar}>
              Voltar
            </button>
          ) : null}
          {!ultimo && (
            <button type="button" className="tour-pular" onClick={() => onFechar(false)}>
              {passo.rotuloPular ?? "Pular tour"}
            </button>
          )}
          <button ref={principalRef} type="button" className="tour-principal" onClick={avancar}>
            {passo.rotuloProximo ?? (ultimo ? "Entendi" : "Próximo")}
          </button>
        </div>
      </div>
    </div>
  );
}
