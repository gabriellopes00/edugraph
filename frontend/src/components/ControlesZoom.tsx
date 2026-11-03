/** Barra flutuante de zoom, compartilhada pelo explorador e pelo laboratório. */

import type { ReactNode } from "react";

/** Aproximar, afastar e centralizar o grafo. */
export function ControlesZoom(props: {
  aoAproximar: () => void;
  aoAfastar: () => void;
  aoCentralizar: () => void;
}) {
  const traco = (filhos: ReactNode) => (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {filhos}
    </svg>
  );
  return (
    <div className="zoom-controles" role="group" aria-label="Zoom do grafo">
      <button type="button" onClick={props.aoAproximar} aria-label="Aproximar o grafo" title="Aproximar (+)">
        {traco(<path d="M12 5v14M5 12h14" />)}
      </button>
      <button type="button" onClick={props.aoAfastar} aria-label="Afastar o grafo" title="Afastar (−)">
        {traco(<path d="M5 12h14" />)}
      </button>
      <button type="button" onClick={props.aoCentralizar} aria-label="Centralizar o grafo" title="Centralizar (0)">
        {traco(
          <>
            <path d="M4 9V5h4M20 9V5h-4M4 15v4h4M20 15v4h-4" />
          </>,
        )}
      </button>
    </div>
  );
}
