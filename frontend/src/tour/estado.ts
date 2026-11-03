/**
 * Lógica pura do tour de boas-vindas — ADR-0013.
 *
 * Fica fora do componente para poder ser testada sem navegador: quais
 * tours já foram vistos, quais passos têm alvo na tela e onde cabe o
 * balão de cada passo. Sem imports locais: o teste transpila só este
 * arquivo.
 */

export type NomeDoTour = "lab" | "resultado" | "explorador";

/** O mínimo de `localStorage` que o tour usa (e que o teste simula). */
export interface Armazenamento {
  getItem(chave: string): string | null;
  setItem(chave: string, valor: string): void;
}

const chaveDoTour = (nome: NomeDoTour) => `edugraph.tour.v1.${nome}`;

function armazenamentoDoNavegador(): Armazenamento | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

/** Já viu (ou dispensou) este tour? Sem armazenamento, vale "não": ele aparece de novo. */
export function jaVisto(nome: NomeDoTour, armazem: Armazenamento | null = armazenamentoDoNavegador()): boolean {
  try {
    return armazem?.getItem(chaveDoTour(nome)) === "1";
  } catch {
    return false;
  }
}

export function marcarVisto(nome: NomeDoTour, armazem: Armazenamento | null = armazenamentoDoNavegador()): void {
  try {
    armazem?.setItem(chaveDoTour(nome), "1");
  } catch {
    /* sem armazenamento: o tour só se repete na próxima visita */
  }
}

/**
 * `?tour` força o tour ao abrir (útil no dia da apresentação) e `?semtour`
 * o desliga (as capturas da figura 9 precisam da tela livre).
 */
export function opcoesDaUrl(search: string): { forcar: boolean; desligar: boolean } {
  const parametros = new URLSearchParams(search);
  return { forcar: parametros.has("tour"), desligar: parametros.has("semtour") };
}

/** Passos cujo alvo existe na tela; os que não têm alvo (boas-vindas) ficam sempre. */
export function passosVisiveis<T extends { alvo?: string; opcional?: boolean }>(
  passos: readonly T[],
  existe: (seletor: string) => boolean,
): T[] {
  return passos.filter((p) => !p.alvo || !p.opcional || existe(p.alvo));
}

export type Lado = "direita" | "esquerda" | "baixo" | "cima" | "dentro";

export interface Retangulo {
  left: number;
  top: number;
  width: number;
  height: number;
}

export interface Posicao {
  top: number;
  left: number;
  lado: Lado | "centro";
}

const limitar = (v: number, min: number, max: number) => Math.max(min, Math.min(v, Math.max(min, max)));

/**
 * Onde pôr o balão ao lado do alvo.
 *
 * Tenta o lado preferido e, se o balão não couber inteiro na tela, os
 * outros; se nenhum couber (alvo enorme, como o grafo), centra o balão
 * dentro do alvo. Sem alvo, centra na tela.
 */
export function posicionarBalao(
  alvo: Retangulo | null,
  balao: { w: number; h: number },
  tela: { w: number; h: number },
  preferido: Lado = "direita",
  margem = 12,
  folga = 16,
): Posicao {
  const { w, h } = balao;
  if (!alvo) {
    return { left: limitar((tela.w - w) / 2, margem, tela.w - w - margem), top: limitar((tela.h - h) / 2, margem, tela.h - h - margem), lado: "centro" };
  }
  const meioX = alvo.left + alvo.width / 2;
  const meioY = alvo.top + alvo.height / 2;
  const topoCentrado = limitar(meioY - h / 2, margem, tela.h - h - margem);
  const esquerdaCentrada = limitar(meioX - w / 2, margem, tela.w - w - margem);
  const candidatos: Record<Lado, { left: number; top: number }> = {
    direita: { left: alvo.left + alvo.width + folga, top: topoCentrado },
    esquerda: { left: alvo.left - folga - w, top: topoCentrado },
    baixo: { left: esquerdaCentrada, top: alvo.top + alvo.height + folga },
    cima: { left: esquerdaCentrada, top: alvo.top - folga - h },
    dentro: { left: esquerdaCentrada, top: topoCentrado },
  };
  const cabe = (c: { left: number; top: number }) =>
    c.left >= margem && c.left + w <= tela.w - margem && c.top >= margem && c.top + h <= tela.h - margem;

  const ordem: Lado[] = [preferido, "direita", "esquerda", "baixo", "cima", "dentro"];
  for (const lado of new Set(ordem)) {
    if (lado === "dentro" || cabe(candidatos[lado])) return { ...candidatos[lado], lado };
  }
  return { ...candidatos.dentro, lado: "dentro" };
}
