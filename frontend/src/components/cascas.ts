/**
 * Contornos das comunidades — ADR-0013.
 *
 * Uma bolha translúcida envolve os nós de cada comunidade e leva o nome
 * dela. É desenhada num canvas à parte, **atrás** do canvas do
 * Cytoscape, e redesenhada a cada quadro dele: a bolha acompanha zoom,
 * arraste e animação dos nós sem que o grafo saiba que ela existe.
 *
 * O contorno é o fecho convexo de um círculo em volta de cada nó, então
 * os cantos saem arredondados. Em grafo grande (milhares de nós) o fecho
 * deixa de dizer algo e custa caro: quem usa decide `ativo`.
 */

import { useEffect, useRef } from "react";
import type { Core } from "cytoscape";

import { themeColor } from "../palette";

export interface Casca {
  ids: string[];
  /** Cor da bolha (hex). */
  cor: string;
  rotulo?: string;
  /** Contorno tracejado e sem preenchimento forte: a "resposta certa" da revelação. */
  tracejada?: boolean;
  /** Escreve o rótulo embaixo do contorno, para não colidir com o nome da comunidade. */
  rotuloEmbaixo?: boolean;
}

type Ponto = { x: number; y: number };

/** Fecho convexo (cadeia monótona de Andrew). */
export function fechoConvexo(pontos: Ponto[]): Ponto[] {
  const ordenados = [...pontos].sort((a, b) => a.x - b.x || a.y - b.y);
  if (ordenados.length < 3) return ordenados;
  const cruz = (o: Ponto, a: Ponto, b: Ponto) => (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
  const metade = (lista: Ponto[]) => {
    const saida: Ponto[] = [];
    for (const p of lista) {
      while (saida.length >= 2 && cruz(saida[saida.length - 2], saida[saida.length - 1], p) <= 0) saida.pop();
      saida.push(p);
    }
    saida.pop();
    return saida;
  };
  return [...metade(ordenados), ...metade([...ordenados].reverse())];
}

function comAlfa(hex: string, alfa: number): string {
  const limpo = hex.replace("#", "");
  const cheio = limpo.length === 3 ? [...limpo].map((c) => c + c).join("") : limpo;
  const n = parseInt(cheio, 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alfa})`;
}

/** Pontos em volta de cada nó: o fecho deles é a bolha, com cantos redondos. */
function inflar(centros: Ponto[], raio: number): Ponto[] {
  const saida: Ponto[] = [];
  for (const c of centros) {
    for (let i = 0; i < 12; i++) {
      const a = (2 * Math.PI * i) / 12;
      saida.push({ x: c.x + raio * Math.cos(a), y: c.y + raio * Math.sin(a) });
    }
  }
  return saida;
}

export function useCascas(cy: Core | null, cascas: Casca[], tema: string, ativo = true) {
  const cascasRef = useRef(cascas);
  const temaRef = useRef(tema);
  const desenharRef = useRef<() => void>(() => {});
  cascasRef.current = cascas;
  temaRef.current = tema;

  useEffect(() => {
    if (!cy || !ativo) return;
    const host = cy.container();
    const pai = host?.parentElement;
    if (!host || !pai) return;

    const canvas = document.createElement("canvas");
    canvas.className = "cascas-canvas";
    canvas.setAttribute("aria-hidden", "true");
    pai.insertBefore(canvas, host);

    let quadro = 0;
    const desenhar = () => {
      quadro = 0;
      if (cy.destroyed()) return;
      const largura = host.clientWidth;
      const altura = host.clientHeight;
      const dpr = window.devicePixelRatio || 1;
      if (canvas.width !== Math.round(largura * dpr) || canvas.height !== Math.round(altura * dpr)) {
        canvas.width = Math.round(largura * dpr);
        canvas.height = Math.round(altura * dpr);
      }
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, largura, altura);

      const tinta = themeColor("--text", "#1a1915");
      const papel = themeColor("--paper", "#fbfaf7");
      const raio = Math.min(34, Math.max(11, 17 * cy.zoom()));

      for (const casca of cascasRef.current) {
        const centros: Ponto[] = [];
        for (const id of casca.ids) {
          const no = cy.getElementById(id);
          if (no.empty() || no.style("display") === "none" || Number(no.style("opacity")) < 0.2) continue;
          centros.push(no.renderedPosition());
        }
        if (centros.length === 0) continue;
        const fecho = fechoConvexo(inflar(centros, raio));
        if (fecho.length < 3) continue;

        ctx.beginPath();
        fecho.forEach((p, i) => (i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y)));
        ctx.closePath();
        ctx.fillStyle = comAlfa(casca.cor, casca.tracejada ? 0.04 : 0.14);
        ctx.fill();
        ctx.lineJoin = "round";
        ctx.lineWidth = casca.tracejada ? 1.6 : 1.4;
        ctx.setLineDash(casca.tracejada ? [7, 5] : []);
        ctx.strokeStyle = casca.tracejada ? comAlfa(tinta, 0.55) : comAlfa(casca.cor, 0.7);
        ctx.stroke();
        ctx.setLineDash([]);

        if (casca.rotulo) {
          const meio = fecho.reduce((s, p) => s + p.x, 0) / fecho.length;
          const embaixo = casca.rotuloEmbaixo === true;
          const y = embaixo ? Math.max(...fecho.map((p) => p.y)) + 5 : Math.min(...fecho.map((p) => p.y)) - 5;
          ctx.font = `${embaixo ? "italic 500 12px" : "600 13px"} "Source Sans 3", system-ui, sans-serif`;
          ctx.textAlign = "center";
          ctx.textBaseline = embaixo ? "top" : "bottom";
          ctx.lineWidth = 4;
          ctx.strokeStyle = comAlfa(papel, 0.9);
          ctx.strokeText(casca.rotulo, meio, y);
          ctx.fillStyle = embaixo ? comAlfa(tinta, 0.75) : tinta;
          ctx.fillText(casca.rotulo, meio, y);
        }
      }
    };
    const agendar = () => {
      if (!quadro) quadro = requestAnimationFrame(desenhar);
    };
    desenharRef.current = agendar;

    cy.on("render viewport resize", agendar);
    agendar();
    return () => {
      cy.off("render viewport resize", agendar);
      if (quadro) cancelAnimationFrame(quadro);
      canvas.remove();
      desenharRef.current = () => {};
    };
  }, [cy, ativo]);

  // Contornos ou tema novos: redesenha sem esperar o Cytoscape se mexer.
  useEffect(() => {
    desenharRef.current();
  }, [cascas, tema]);
}
