/**
 * Aba na borda da figura que abre e fecha uma das colunas laterais.
 *
 * Fica na figura, e não dentro da coluna, para continuar à vista com a coluna
 * fechada. A preferência de cada lado é lembrada no navegador, quando ele deixa.
 */

import { useCallback, useState } from "react";

const CHAVE = "edugraph-colunas";

type Lado = "esquerda" | "direita";

function lerPreferencias(): Record<Lado, boolean> {
  try {
    const salvo = JSON.parse(localStorage.getItem(CHAVE) ?? "{}") as Partial<Record<Lado, unknown>>;
    return { esquerda: salvo.esquerda !== false, direita: salvo.direita !== false };
  } catch {
    return { esquerda: true, direita: true };
  }
}

/** Estado aberto/fechado das duas colunas. Abertas por padrão. */
export function useColunas() {
  const [abertas, setAbertas] = useState(lerPreferencias);
  const definir = useCallback((lado: Lado, aberta: boolean) => {
    setAbertas((atual) => {
      if (atual[lado] === aberta) return atual;
      const novo = { ...atual, [lado]: aberta };
      try {
        localStorage.setItem(CHAVE, JSON.stringify(novo));
      } catch {
        /* sem armazenamento: a escolha vale só nesta sessão */
      }
      return novo;
    });
  }, []);
  return { abertas, definir };
}

export function Alca(props: {
  lado: Lado;
  aberta: boolean;
  rotulo: string;
  controla: string;
  onAlternar: () => void;
}) {
  // A seta aponta para onde a coluna vai: para fora da tela ao fechar, para dentro ao abrir.
  const apontaEsquerda = (props.lado === "esquerda") === props.aberta;
  return (
    <button
      type="button"
      className={`alca alca-${props.lado}`}
      aria-expanded={props.aberta}
      aria-controls={props.controla}
      title={`${props.aberta ? "Ocultar" : "Mostrar"}: ${props.rotulo}`}
      onClick={props.onAlternar}
    >
      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d={apontaEsquerda ? "M15 5l-7 7 7 7" : "M9 5l7 7-7 7"} />
      </svg>
      <span>{props.rotulo}</span>
    </button>
  );
}
