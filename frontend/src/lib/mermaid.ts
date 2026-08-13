/**
 * Configuração compartilhada do Mermaid.
 *
 * Tanto os diagramas escritos nas TechDocs quanto o grafo de dependências
 * precisam da mesma paleta — a do cockpit, lida dos tokens CSS em vez de
 * fixada aqui, para acompanhar a troca de tema.
 */
import mermaid from 'mermaid';

/** Último tema aplicado; a paleta só é reconfigurada quando ele muda. */
let appliedTheme: string | null = null;

function readToken(css: CSSStyleDeclaration, name: string, fallback: string): string {
  return css.getPropertyValue(name).trim() || fallback;
}

/**
 * Cor segura para entrar num `classDef`.
 *
 * O Mermaid separa os estilos de um `classDef` por vírgula, então um token
 * `rgba(22, 46, 55, 0.34)` — como os tokens de linha do tema — quebraria o
 * diagrama inteiro. Nesses casos vale o fallback.
 */
function readColor(css: CSSStyleDeclaration, name: string, fallback: string): string {
  const value = readToken(css, name, '');
  return value && !value.includes(',') && !value.includes(' ') ? value : fallback;
}

/** Cores do tema atual, para quem precisa montar `classDef` na mão. */
export function graphPalette() {
  const css = getComputedStyle(document.documentElement);
  const txtFaint = readColor(css, '--txt-faint', '#849da7');
  return {
    surface: readColor(css, '--surface', '#161f24'),
    surface2: readColor(css, '--surface-2', '#1d272d'),
    surface3: readColor(css, '--surface-3', '#26323a'),
    txt: readColor(css, '--txt', '#e4edf1'),
    txtDim: readColor(css, '--txt-dim', '#94a7b1'),
    txtFaint,
    // Os tokens de linha são rgba() e não passam pelo `classDef`; o cinza do
    // texto apagado é a borda equivalente e é hexadecimal nos dois temas.
    line: txtFaint,
    visor: readColor(css, '--visor', '#2ed3ec'),
    crest: readColor(css, '--crest', '#e9b93f'),
    alert: readColor(css, '--alert', '#e05252'),
    ok: readColor(css, '--ok', '#3fbf87')
  };
}

/** Inicializa o Mermaid, ou o reconfigura se o tema tiver mudado. */
export function initMermaid(): void {
  if (typeof document === 'undefined') return;

  const dark = document.documentElement.classList.contains('dark');
  const themeKey = dark ? 'dark' : 'light';
  if (themeKey === appliedTheme) return;

  const p = graphPalette();
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: 'loose',
    theme: 'base',
    fontFamily: 'JetBrains Mono, ui-monospace, monospace',
    flowchart: {
      htmlLabels: false,
      padding: 18
    },
    themeVariables: {
      darkMode: dark,
      background: p.surface2,
      primaryColor: p.surface3,
      primaryTextColor: p.txt,
      primaryBorderColor: p.visor,
      lineColor: p.txtFaint,
      secondaryColor: p.crest,
      tertiaryColor: p.surface
    }
  });
  appliedTheme = themeKey;
}

/** Renderiza uma definição Mermaid e devolve o SVG. */
export async function renderMermaid(id: string, definition: string): Promise<string> {
  initMermaid();
  const { svg } = await mermaid.render(id, definition);
  return svg;
}
