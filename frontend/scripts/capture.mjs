/**
 * Capturas da interface para a figura 9 do artigo — spec C-05.
 *
 * Abre a interface num navegador headless (Edge ou Chrome, via o
 * protocolo DevTools), monta cada cena pelos próprios controles da tela e
 * grava `ui-*.png` + `ui-*.caption.txt` em `results/figures/`. Sem
 * dependência nova: usa o WebSocket nativo do Node 22+.
 *
 * Pré-requisitos: o front compilado (`npm run build`) e a API no ar:
 *
 *     python -m edugraph api serve --root data/processed --root data/fixtures
 *     npm run capture
 *
 * Opções: `--url http://127.0.0.1:8000`, `--out ../results/figures`.
 * Variável `EDUGRAPH_BROWSER` aponta outro navegador, se preciso.
 *
 * As capturas são material complementar do capítulo 3: não são
 * reproduzíveis byte a byte (o layout anima e o antialiasing varia), ao
 * contrário das figuras de `reporting/figures.py`.
 */

import { spawn } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const aqui = fileURLToPath(new URL(".", import.meta.url));
const args = Object.fromEntries(
  process.argv.slice(2).reduce((pares, arg, i, todos) => {
    if (arg.startsWith("--")) pares.push([arg.slice(2), todos[i + 1]]);
    return pares;
  }, []),
);
const URL_APP = args.url ?? "http://127.0.0.1:8000";
const SAIDA = resolve(args.out ?? join(aqui, "..", "..", "results", "figures"));
const LARGURA = 1600;
const ALTURA = 1000;
const PORTA = 9223;

const CANDIDATOS = [
  process.env.EDUGRAPH_BROWSER,
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
].filter(Boolean);

/**
 * As cenas da figura 9, na ordem do roteiro de `frontend/README.md`.
 * `precisa` é o dataset sem o qual a cena é pulada (o OULAD fica fora do
 * git; quem não o tem ainda gera as duas primeiras).
 */
const CENAS = [
  {
    nome: "ui-1-comunidades-synthetic_v1",
    precisa: "synthetic_v1",
    dataset: "synthetic_v1",
    projecao: "student_simple",
    particao: "louvain__student_simple",
    metrica: "Igual",
    legenda:
      "Interface do edugraph sobre a base sintética (synthetic_v1, projeção aluno↔aluno): " +
      "as três comunidades encontradas pelo Louvain (Q = 0,467), cada uma com uma cor e uma " +
      "forma, correspondem às três áreas plantadas no gerador. Captura da spec C-05.",
  },
  {
    nome: "ui-2-intermediacao-synthetic_v1",
    precisa: "synthetic_v1",
    dataset: "synthetic_v1",
    projecao: "student_simple",
    particao: "louvain__student_simple",
    metrica: "Intermediação",
    no: "S100055",
    legenda:
      "Mesma rede com o tamanho dos nós pela intermediação: os alunos que ligam as comunidades " +
      "crescem. O painel mostra o nó selecionado com as três métricas e a posição no ranking " +
      "(1º em grau e em intermediação, 15º em autovetor). Captura da spec C-05.",
  },
  {
    nome: "ui-3-disciplinas-criticas-oulad_module_presentation",
    precisa: "oulad_module_presentation",
    dataset: "oulad_module_presentation",
    projecao: "discipline_simple",
    particao: "louvain__discipline_simple",
    metrica: "Intermediação",
    legenda:
      "Projeção disciplina↔disciplina do OULAD (22 disciplinas, módulo × apresentação), com o " +
      "tamanho pela intermediação: as maiores são as disciplinas críticas da spec C-03 " +
      "(FFF_2014B, DDD_2014J, FFF_2014J). Cores pelas comunidades do Louvain. Captura da spec C-05.",
  },
  {
    nome: "ui-4-alunos-ava-oulad_vle_bbb_2013j",
    precisa: "oulad_vle_bbb_2013j",
    dataset: "oulad_vle_bbb_2013j",
    projecao: "student_simple",
    particao: "louvain__student_simple",
    metrica: "Autovetor",
    espera: 25_000,
    legenda:
      "Os 1.870 alunos da coorte BBB 2013J ligados pelo uso do AVA (1,75 milhão de arestas), " +
      "desenhados pelo esqueleto da API: as 2 ligações mais fortes de cada aluno, como diz a " +
      "faixa de aviso. Tamanho pelo autovetor; cores pelo Louvain (Q = 0,039, estrutura fraca). " +
      "Captura da spec C-05.",
  },
];

// ---------------------------------------------------------------------
// Protocolo DevTools, o mínimo necessário
// ---------------------------------------------------------------------

const dormir = (ms) => new Promise((ok) => setTimeout(ok, ms));

async function esperarHttp(url, limiteMs) {
  const fim = Date.now() + limiteMs;
  while (Date.now() < fim) {
    try {
      const r = await fetch(url);
      if (r.ok) return r;
    } catch {
      // ainda subindo
    }
    await dormir(250);
  }
  throw new Error(`sem resposta de ${url} em ${limiteMs / 1000}s`);
}

function conectar(wsUrl) {
  return new Promise((ok, falha) => {
    const ws = new WebSocket(wsUrl);
    let seq = 0;
    const pendentes = new Map();
    const ouvintes = new Map();
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && pendentes.has(msg.id)) {
        const { ok: resolver, falha: rejeitar } = pendentes.get(msg.id);
        pendentes.delete(msg.id);
        msg.error ? rejeitar(new Error(msg.error.message)) : resolver(msg.result);
      } else if (msg.method && ouvintes.has(msg.method)) {
        for (const f of ouvintes.get(msg.method)) f(msg.params);
      }
    };
    ws.onerror = () => falha(new Error(`não conectou em ${wsUrl}`));
    ws.onopen = () =>
      ok({
        enviar: (method, params = {}) =>
          new Promise((resolver, rejeitar) => {
            const id = ++seq;
            pendentes.set(id, { ok: resolver, falha: rejeitar });
            ws.send(JSON.stringify({ id, method, params }));
          }),
        uma: (method) =>
          new Promise((resolver) => {
            const lista = ouvintes.get(method) ?? [];
            const f = (p) => {
              ouvintes.set(method, (ouvintes.get(method) ?? []).filter((g) => g !== f));
              resolver(p);
            };
            ouvintes.set(method, [...lista, f]);
          }),
        fechar: () => ws.close(),
      });
  });
}

// ---------------------------------------------------------------------
// Ações na página
// ---------------------------------------------------------------------

async function avaliar(cdp, expressao) {
  const r = await cdp.enviar("Runtime.evaluate", {
    expression: expressao,
    returnByValue: true,
    awaitPromise: true,
  });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? expressao);
  return r.result.value;
}

async function esperar(cdp, expressao, limiteMs, oQue) {
  const fim = Date.now() + limiteMs;
  while (Date.now() < fim) {
    if (await avaliar(cdp, expressao)) return;
    await dormir(200);
  }
  throw new Error(`tempo esgotado esperando ${oQue}`);
}

/** Seleciona uma opção como o usuário faria, disparando o evento que o React escuta. */
function escolher(indice, valor) {
  return `(() => {
    const s = document.querySelectorAll('select')[${indice}];
    if (!s || ![...s.options].some(o => o.value === ${JSON.stringify(valor)})) return false;
    const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set;
    setter.call(s, ${JSON.stringify(valor)});
    s.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  })()`;
}

const CY = "document.querySelector('.graph-canvas')?._cyreg?.cy";

/**
 * O grafo **desta** projeção está desenhado e parado.
 *
 * Contar os nós contra a API é o que separa o grafo novo do anterior, que
 * continua na tela enquanto o novo carrega; depois espera o layout do
 * fcose (que anima por ~0,7 s) parar de mover os nós.
 */
async function esperarGrafoParado(cdp, dataset, projecao, limiteMs) {
  const n = await avaliar(
    cdp,
    `fetch('/datasets/${dataset}/projections/${projecao}?max_edges=1').then(r => r.json()).then(g => g.truncation.n_nodes)`,
  );
  await esperar(
    cdp,
    `!document.querySelector('.vazio') && !!${CY} && ${CY}.nodes().length === ${n}`,
    limiteMs,
    `o grafo de ${projecao} (${n} nós)`,
  );
  const soma = `(() => { let s = 0; ${CY}.nodes().forEach(n => { const p = n.position(); s += p.x + 3 * p.y; }); return s; })()`;
  let anterior = await avaliar(cdp, soma);
  for (let i = 0; i < 60; i++) {
    await dormir(400);
    const atual = await avaliar(cdp, soma);
    if (Math.abs(atual - anterior) < 1e-6) break;
    anterior = atual;
  }
  await dormir(700); // transições de cor e tamanho (450 ms)
}

async function montarCena(cdp, cena) {
  const temDataset = await avaliar(
    cdp,
    `[...document.querySelectorAll('select')[0].options].some(o => o.value === ${JSON.stringify(cena.precisa)})`,
  );
  if (!temDataset) return false;

  await avaliar(cdp, escolher(0, cena.dataset));
  await esperar(cdp, escolher(1, cena.projecao), 10_000, `a projeção ${cena.projecao}`);
  await esperarGrafoParado(cdp, cena.dataset, cena.projecao, cena.espera ?? 15_000);
  await esperar(cdp, escolher(2, cena.particao), 10_000, `a partição ${cena.particao}`);
  await esperar(cdp, "document.querySelectorAll('.legenda li').length > 0", 10_000, "a legenda");
  // O botão da métrica só aparece quando as centralidades chegam com o grafo.
  await esperar(
    cdp,
    `(() => { const b = [...document.querySelectorAll('.segmentado button')].find(b => b.textContent.trim() === ${JSON.stringify(cena.metrica)}); b?.click(); return !!b; })()`,
    10_000,
    `o botão ${cena.metrica}`,
  );
  await avaliar(cdp, `(${CY}.emit('tap'), true)`); // limpa seleção anterior
  if (cena.no) {
    await avaliar(cdp, `(${CY}.getElementById(${JSON.stringify(cena.no)}).emit('tap'), true)`);
    await esperar(cdp, "!!document.querySelector('.node-panel')", 5_000, "o painel do nó");
  }
  await dormir(1_200); // contadores da faixa de números e transições
  return true;
}

// ---------------------------------------------------------------------

async function main() {
  const navegador = CANDIDATOS.find((c) => existsSync(c));
  if (!navegador) {
    throw new Error("nenhum Edge/Chrome encontrado; aponte um em EDUGRAPH_BROWSER");
  }
  await esperarHttp(`${URL_APP}/health`, 5_000).catch(() => {
    throw new Error(
      `a API não respondeu em ${URL_APP}. Suba antes:\n` +
        "  python -m edugraph api serve --root data/processed --root data/fixtures",
    );
  });

  const perfil = mkdtempSync(join(tmpdir(), "edugraph-capture-"));
  const proc = spawn(
    navegador,
    [
      "--headless=new",
      `--remote-debugging-port=${PORTA}`,
      `--user-data-dir=${perfil}`,
      `--window-size=${LARGURA},${ALTURA}`,
      "--hide-scrollbars",
      "--no-first-run",
      "--no-default-browser-check",
      "about:blank",
    ],
    { stdio: "ignore" },
  );

  try {
    await esperarHttp(`http://127.0.0.1:${PORTA}/json/version`, 15_000);
    const alvo = await (
      await fetch(`http://127.0.0.1:${PORTA}/json/new?about:blank`, { method: "PUT" })
    ).json();
    const cdp = await conectar(alvo.webSocketDebuggerUrl);
    await cdp.enviar("Page.enable");
    await cdp.enviar("Runtime.enable");
    await cdp.enviar("Emulation.setDeviceMetricsOverride", {
      width: LARGURA,
      height: ALTURA,
      deviceScaleFactor: 2, // 3200 × 2000: nítido na impressão
      mobile: false,
    });
    await cdp.enviar("Emulation.setEmulatedMedia", {
      features: [{ name: "prefers-reduced-motion", value: "no-preference" }],
    });

    const carregou = cdp.uma("Page.loadEventFired");
    // O laboratório é a aba padrão; as cenas da figura 9 são do explorador, sem o tour de boas-vindas.
    await cdp.enviar("Page.navigate", { url: `${URL_APP}/?semtour#explorar` });
    await carregou;
    await esperar(cdp, "document.querySelectorAll('select').length >= 2", 15_000, "os seletores");

    mkdirSync(SAIDA, { recursive: true });
    for (const cena of CENAS) {
      process.stdout.write(`[capture] ${cena.nome}… `);
      if (!(await montarCena(cdp, cena))) {
        console.log(`pulada (dataset ${cena.precisa} não está sob as raízes da API)`);
        continue;
      }
      const { data } = await cdp.enviar("Page.captureScreenshot", { format: "png" });
      writeFileSync(join(SAIDA, `${cena.nome}.png`), Buffer.from(data, "base64"));
      writeFileSync(join(SAIDA, `${cena.nome}.caption.txt`), `${cena.legenda}\n`, "utf-8");
      console.log("ok");
    }
    cdp.fechar();
    console.log(`[capture] gravado em ${SAIDA}`);
    console.log("[capture] regenere o índice: python -m edugraph figures --index");
  } finally {
    proc.kill();
    await dormir(500);
    try {
      rmSync(perfil, { recursive: true, force: true });
    } catch {
      // o navegador pode segurar o perfil por um instante no Windows
    }
  }
}

main().catch((erro) => {
  console.error(`[capture] ${erro.message}`);
  process.exit(1);
});
