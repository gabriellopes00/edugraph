/**
 * Mantém o Cytoscape do tamanho da caixa que o contém.
 *
 * O Cytoscape só escuta a janela: quando uma coluna lateral abre ou fecha, o
 * contêiner do grafo muda de largura sem a janela mudar, e o desenho fica
 * cortado ou com sobra. Aqui um `ResizeObserver` chama `cy.resize()` e, em
 * seguida, enquadra de novo — com um pequeno atraso, para esperar a
 * transição das colunas terminar em vez de enquadrar a cada quadro dela.
 */

import { useEffect, useRef, type RefObject } from "react";
import type { Core } from "cytoscape";

const ATRASO_MS = 120;
/** Variações menores que isto (em px) são arredondamento, não mudança de layout. */
const TOLERANCIA_PX = 2;

export function useRedimensionar(
  host: RefObject<HTMLElement | null>,
  cyRef: RefObject<Core | null>,
  reenquadrar: (cy: Core) => void,
) {
  const reenquadrarRef = useRef(reenquadrar);
  reenquadrarRef.current = reenquadrar;

  useEffect(() => {
    const elemento = host.current;
    if (!elemento || typeof ResizeObserver === "undefined") return;
    let ultimo: { w: number; h: number } | null = null;
    let espera = 0;
    const observador = new ResizeObserver(([entrada]) => {
      const { width: w, height: h } = entrada.contentRect;
      const anterior = ultimo;
      ultimo = { w, h };
      // A primeira medida é a do desenho inicial, que o layout já enquadra.
      if (!anterior) return;
      if (Math.abs(w - anterior.w) < TOLERANCIA_PX && Math.abs(h - anterior.h) < TOLERANCIA_PX) return;
      window.clearTimeout(espera);
      espera = window.setTimeout(() => {
        const cy = cyRef.current;
        if (!cy || cy.destroyed()) return;
        cy.resize();
        reenquadrarRef.current(cy);
      }, ATRASO_MS);
    });
    observador.observe(elemento);
    return () => {
      window.clearTimeout(espera);
      observador.disconnect();
    };
  }, [host, cyRef]);
}
