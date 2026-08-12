/**
 * Tradução do grafo de dependências para uma definição Mermaid.
 *
 * Função pura de propósito: é a parte com regra (formas, classes, ciclos,
 * escape de rótulo) e a que quebra o diagrama inteiro quando erra, então fica
 * fora do componente para poder ser exercitada isoladamente.
 */
import type { DependencyGraph, GraphNode } from '$lib/api';

export interface GraphPalette {
  surface: string;
  surface2: string;
  surface3: string;
  txt: string;
  txtDim: string;
  txtFaint: string;
  line: string;
  visor: string;
  crest: string;
  alert: string;
  ok: string;
}

/**
 * Escapa um rótulo para caber entre aspas numa definição Mermaid.
 *
 * Nomes de projeto vêm do `project-info.yml` e podem trazer qualquer coisa;
 * uma aspa solta quebra o diagrama inteiro.
 */
export function mermaidLabel(text: string): string {
  return (text || '')
    .replace(/["`]/g, '#quot;')
    .replace(/[\r\n]+/g, ' ')
    .trim();
}

/** Folga lateral do rótulo, em caracteres, para nó comum e para hub. */
const LABEL_SIDE_PAD = 2;
const HUB_LABEL_SIDE_PAD = 3;

/**
 * Largura mínima do rótulo, em caracteres.
 *
 * A caixa do Mermaid é dimensionada pelo texto, então um nome curto — `STRIX`,
 * `IDEA 2` — sai com uma caixa apertada mesmo quando é o hub do grafo e deveria
 * ser a maior. Como a fonte do diagrama é monoespaçada, dá para garantir um piso
 * de largura completando o rótulo com o caractere U+2800 (Braille Pattern Blank).
 *
 * O parser interno do Mermaid executa .trim() em espaços normais e \u00A0 (NBSP),
 * mas preserva U+2800 intacto, permitindo que o Dagre meça a largura e desenhe
 * as caixas e setas com as dimensões corretas.
 */
const MIN_LABEL_LEN = 16;
const MIN_HUB_LABEL_LEN = 22;

/** Centraliza o rótulo dentro da largura mínima usando U+2800. */
export function padLabel(label: string, isHub: boolean): string {
  const sidePad = isHub ? HUB_LABEL_SIDE_PAD : LABEL_SIDE_PAD;
  const minLen = isHub ? MIN_HUB_LABEL_LEN : MIN_LABEL_LEN;
  const total = Math.max(label.length + sidePad * 2, minLen);
  const extra = total - label.length;
  const left = Math.ceil(extra / 2);
  const padChar = String.fromCharCode(0x2800);
  return padChar.repeat(left) + label + padChar.repeat(extra - left);
}

export function isWebsiteType(type?: string | null): boolean {
  const t = (type || '').toLowerCase();
  return t === 'website' || t === 'frontend' || t === 'web' || t === 'spa' || t === 'ui';
}

export function isDatabaseType(type?: string | null): boolean {
  const t = (type || '').toLowerCase();
  return t === 'database' || t === 'db';
}

/** A classe visual de um nó, na ordem em que os estados se sobrepõem. */
export function nodeClass(node: GraphNode): string {
  if (node.is_root) return 'raiz';
  if (!node.resolved) return 'fantasma';
  if ((node.lifecycle || '').toLowerCase() === 'deprecated') return 'depreciado';
  if (!node.in_scope) return 'fora';
  if (node.is_external) return 'externo';
  if (isWebsiteType(node.type)) return 'website';
  if (isDatabaseType(node.type)) return 'database';
  if (node.is_resource) return 'recurso';
  return 'service';
}

export function buildGraphDefinition(graph: DependencyGraph, palette: GraphPalette): string {
  const p = palette;
  const lines = ['flowchart LR'];

  // Contagem de arestas ENTRANTES por nó (setas apontando para o nó)
  const inDegreeCounts = new Map<string, number>();
  for (const node of graph.nodes) {
    inDegreeCounts.set(node.id, 0);
  }
  for (const edge of graph.edges) {
    inDegreeCounts.set(edge.target, (inDegreeCounts.get(edge.target) || 0) + 1);
  }

  let maxInEdges = 0;
  for (const count of inDegreeCounts.values()) {
    if (count > maxInEdges) maxInEdges = count;
  }

  // O nó só ganha destaque visual de hub e aumento de caixa se tiver MAIS DE 3 setas apontando para ele (> 3)
  const hubNodeIds = new Set<string>();
  if (maxInEdges > 3) {
    for (const [id, count] of inDegreeCounts.entries()) {
      if (count === maxInEdges) {
        hubNodeIds.add(id);
      }
    }
  }

  for (const node of graph.nodes) {
    const rawLabel = mermaidLabel(node.name);
    const isHub = hubNodeIds.has(node.id);
    const label = padLabel(rawLabel, isHub);
    const isDb = isDatabaseType(node.type);
    if (isDb) {
      lines.push(`  ${node.id}[("${label}")]`);
    } else if (node.is_resource) {
      lines.push(`  ${node.id}{{"${label}"}}`);
    } else if (node.is_external) {
      lines.push(`  ${node.id}[["${label}"]]`);
    } else if (!node.resolved) {
      lines.push(`  ${node.id}(["${label}"])`);
    } else {
      lines.push(`  ${node.id}["${label}"]`);
    }
  }

  for (const edge of graph.edges) {
    lines.push(`  ${edge.source} --> ${edge.target}`);
  }

  for (const node of graph.nodes) {
    if (node.component_id !== null) {
      const tooltip = mermaidLabel(
        [node.type, node.lifecycle, node.owner].filter(Boolean).join(' · ')
      );
      lines.push(`  click ${node.id} href "/catalog/${node.component_id}" "${tooltip}"`);
    }
  }

  lines.push(
    // Ordem de destaque:
    // 1. Component Website (Destaque visor 1.5px)
    `  classDef website fill:${p.surface3},stroke:${p.visor},stroke-width:1.5px,color:${p.txt}`,

    // 2. Component API / Service (Destaque crest 1.5px)
    `  classDef service fill:${p.surface2},stroke:${p.crest},stroke-width:1.5px,color:${p.txt}`,
    `  classDef padrao fill:${p.surface2},stroke:${p.crest},stroke-width:1.5px,color:${p.txt}`,

    // 3. Resource & Database (Destaque sutil / suave: borda fina de 1px)
    `  classDef recurso fill:${p.surface},stroke:${p.line},stroke-width:1px,color:${p.txtDim}`,
    `  classDef database fill:${p.surface},stroke:${p.line},stroke-width:1px,color:${p.txtDim}`,

    // Estados especiais
    `  classDef raiz fill:${p.surface3},stroke:${p.visor},stroke-width:2.5px,color:${p.txt}`,
    `  classDef fora fill:${p.surface},stroke:${p.line},stroke-width:1px,color:${p.txtDim},stroke-dasharray: 5 4`,
    `  classDef fantasma fill:${p.surface},stroke:${p.crest},stroke-width:1.5px,color:${p.crest},stroke-dasharray: 4 3`,
    `  classDef depreciado fill:${p.surface2},stroke:${p.alert},stroke-width:1.5px,color:${p.alert}`,
    `  classDef externo fill:${p.surface3},stroke:${p.ok},stroke-width:1.5px,color:${p.ok}`,

    // Classe para destacar o nó mais consumido (somente quando > 3 setas apontando para ele)
    `  classDef hub stroke-width:3px,font-weight:bold`
  );

  const grouped = new Map<string, string[]>();
  for (const node of graph.nodes) {
    const cls = nodeClass(node);
    grouped.set(cls, [...(grouped.get(cls) || []), node.id]);
  }
  for (const [cls, ids] of grouped) {
    lines.push(`  class ${ids.join(',')} ${cls}`);
  }

  if (hubNodeIds.size > 0) {
    lines.push(`  class ${Array.from(hubNodeIds).join(',')} hub`);
  }

  // Arestas de ciclo em destaque
  graph.edges.forEach((edge, index) => {
    if (edge.in_cycle) {
      lines.push(`  linkStyle ${index} stroke:${p.alert},stroke-width:2px`);
    }
  });

  return lines.join('\n');
}
