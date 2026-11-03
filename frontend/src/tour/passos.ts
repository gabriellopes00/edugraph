/**
 * Textos e alvos dos tours — ADR-0013.
 *
 * Todo o texto que o visitante lê no tour mora aqui, num arquivo só, para
 * o grupo revisar a redação sem tocar em componente. Cada alvo é um
 * `data-tour="..."` posto no elemento da tela. `**assim**` vira negrito.
 */

import type { Lado, NomeDoTour } from "./estado";

export interface Passo {
  /** Seletor CSS do elemento a destacar; sem ele, o passo é um cartão central. */
  alvo?: string;
  /** O passo só vale se o alvo existir (ex.: a revelação não existe em todo dataset). */
  opcional?: boolean;
  titulo: string;
  corpo: string[];
  lado?: Lado;
  /** Faz o contorno pulsar: chama a atenção para o que se deve clicar. */
  pulsar?: boolean;
  rotuloProximo?: string;
  rotuloPular?: string;
}

const alvo = (nome: string) => `[data-tour="${nome}"]`;

export const TOUR_LAB: Passo[] = [
  {
    titulo: "Bem-vindo ao edugraph",
    corpo: [
      "Este sistema mostra como **alunos e disciplinas formam uma rede**, e como dois algoritmos clássicos de grafos (Louvain e Girvan–Newman) encontram grupos nela — sem inteligência artificial.",
      "Você vai montar uma turma, ver a rede nascer passo a passo e ler o resultado: os grupos, quem corre risco de evasão e quem se destaca.",
    ],
    rotuloProximo: "Fazer o tour · 1 min",
    rotuloPular: "Pular e explorar",
  },
  {
    alvo: alvo("abas"),
    lado: "baixo",
    titulo: "Duas telas",
    corpo: [
      "**Laboratório ao vivo** monta uma rede na hora, com uma turma fictícia ou uma amostra de dados reais.",
      "**Explorar resultados** mostra os dados reais do OULAD, já calculados.",
    ],
  },
  {
    alvo: alvo("turma"),
    lado: "direita",
    titulo: "1 · A turma",
    corpo: [
      "De onde vêm os alunos e quantos são. A turma de Computação é **fictícia** e gerada na hora, com três áreas: Desenvolvimento, Infraestrutura e Dados.",
      "**Mistura entre áreas** é quantos alunos cursam também disciplinas de fora da sua área: quanto maior, mais difícil achar os grupos. **Sortear** gera outra turma.",
    ],
  },
  {
    alvo: alvo("rede"),
    lado: "direita",
    titulo: "2 · A rede",
    corpo: [
      "O que ligar a quê. Com **Alunos**, dois alunos se ligam quando cursam a mesma disciplina. Com **Disciplinas**, duas disciplinas se ligam quando têm alunos em comum.",
      "**Ligação mínima** esconde as ligações mais fracas, o que deixa redes grandes legíveis.",
    ],
  },
  {
    alvo: alvo("algoritmo"),
    lado: "baixo",
    titulo: "O algoritmo",
    corpo: [
      "**Louvain** é rápido: cada nó escolhe o grupo em que a rede fica mais bem separada.",
      "**Girvan–Newman** é lento: corta, uma a uma, as ligações que funcionam como ponte entre grupos, até a rede se partir.",
    ],
  },
  {
    alvo: alvo("etapas"),
    lado: "baixo",
    titulo: "As quatro etapas",
    corpo: [
      "A montagem conta quatro momentos: **matrículas**, **projeção**, **algoritmo** e **resultado**. Dá para pular para qualquer um deles.",
    ],
  },
  {
    alvo: alvo("grafo"),
    lado: "dentro",
    titulo: "O grafo",
    corpo: [
      "Cada ponto é um aluno (ou uma disciplina) e cada linha é uma ligação. A forma e a cor mostram o grupo.",
      "Arraste para mover, use a rolagem para aproximar e clique num ponto para ver os detalhes dele.",
    ],
  },
  {
    alvo: alvo("narracao"),
    lado: "esquerda",
    titulo: "A narração",
    corpo: [
      "Aqui o sistema explica, em português, o que está acontecendo em cada etapa. No fim, ele mostra o resultado: os grupos com nome, quem corre risco e quem se destaca.",
    ],
  },
  {
    alvo: alvo("tocar"),
    lado: "cima",
    pulsar: true,
    titulo: "Tudo pronto: aperte ▶",
    corpo: [
      "A rede **só é montada quando você aperta ▶**. Mude os controles quantas vezes quiser; nada roda antes. Depois de uma mudança, aperte ▶ de novo.",
      "Espaço toca e pausa; ← e → andam quadro a quadro. Para rever este tour, use o botão **Tour** no topo.",
    ],
    rotuloProximo: "Entendi",
  },
];

export const TOUR_RESULTADO: Passo[] = [
  {
    alvo: alvo("resumo"),
    opcional: true,
    lado: "esquerda",
    titulo: "O resumo em palavras",
    corpo: [
      "Frases geradas por regra a partir do resultado: quantos grupos, o quanto eles se separam (a **modularidade Q**), quem faz ponte e quem merece atenção.",
    ],
  },
  {
    alvo: alvo("grupos"),
    opcional: true,
    lado: "esquerda",
    titulo: "Os grupos",
    corpo: [
      "Cada cor é um grupo que o algoritmo achou sozinho. O **nome** vem das disciplinas que o grupo mais cursa.",
      "Passe o mouse sobre um grupo para destacá-lo no grafo.",
    ],
  },
  {
    alvo: alvo("perfis"),
    opcional: true,
    lado: "esquerda",
    titulo: "Perfis dos alunos",
    corpo: [
      "**Quem merece atenção** reúne os alunos com sinais de evasão e **Possíveis talentos**, os que se destacam; cada um vem com o porquê. Clique para ver no grafo.",
      "São indicadores calculados só com as matrículas — não são previsões.",
    ],
  },
  {
    alvo: alvo("revelar"),
    opcional: true,
    lado: "esquerda",
    titulo: "Revelar o que o grafo nunca viu",
    corpo: [
      "O algoritmo não sabia das áreas verdadeiras nem de quem foi aprovado. Marque aqui para **conferir** se ele acertou e se os sinais de risco batem com o que aconteceu.",
    ],
    rotuloProximo: "Entendi",
  },
];

export const TOUR_EXPLORADOR: Passo[] = [
  {
    titulo: "Explorar resultados",
    corpo: [
      "Aqui estão os **dados reais do OULAD** (alunos e recursos de uma plataforma de ensino a distância), já calculados: o grafo, os grupos e a importância de cada nó.",
      "Nada é recalculado nesta tela; para montar uma rede na hora, use o Laboratório.",
    ],
    rotuloProximo: "Ver o tour",
    rotuloPular: "Pular",
  },
  {
    alvo: alvo("x-dados"),
    lado: "direita",
    titulo: "1 · Os dados",
    corpo: ["O conjunto de dados lido do disco. Cada um vem de um recorte diferente do OULAD."],
  },
  {
    alvo: alvo("x-projecao"),
    lado: "direita",
    titulo: "2 · A projeção",
    corpo: [
      "Rede de um só tipo de nó: **alunos** ligados por comportamento parecido, ou **disciplinas** (módulos, recursos) ligadas por alunos em comum.",
    ],
  },
  {
    alvo: alvo("x-comunidades"),
    lado: "direita",
    titulo: "3 · As comunidades",
    corpo: [
      "Os grupos encontrados pelo algoritmo, com cor, forma, nome e tamanho. **Q** mede o quanto eles se separam: acima de 0,3, os grupos são bem definidos.",
    ],
  },
  {
    alvo: alvo("x-leitura"),
    opcional: true,
    lado: "direita",
    titulo: "4 · A leitura",
    corpo: [
      "O que o grafo diz, em frases, o papel de cada nó, os perfis dos alunos e, em **Revelar o desfecho**, a conferência com quem foi aprovado, reprovado ou desistiu.",
    ],
  },
  {
    alvo: alvo("x-grafo"),
    lado: "dentro",
    titulo: "O grafo",
    corpo: [
      "Clique num nó para ver o grupo dele, as centralidades e os vizinhos. Para rever este tour, use o botão **Tour** no topo.",
    ],
    rotuloProximo: "Entendi",
  },
];

export const PASSOS: Record<NomeDoTour, Passo[]> = {
  lab: TOUR_LAB,
  resultado: TOUR_RESULTADO,
  explorador: TOUR_EXPLORADOR,
};
