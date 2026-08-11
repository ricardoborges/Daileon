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

/** A classe visual de um nó, na ordem em que os estados se sobrepõem. */
export function nodeClass(node: GraphNode): string {
  if (node.is_root) return 'raiz';
  if (node.is_resource) return 'recurso';
  if (node.is_external) return 'externo';
  if (!node.resolved) return 'fantasma';
  if ((node.lifecycle || '').toLowerCase() === 'deprecated') return 'depreciado';
  if (!node.in_scope) return 'fora';
  return 'padrao';
}

export function buildGraphDefinition(graph: DependencyGraph, palette: GraphPalette): string {
  const p = palette;
  const lines = ['flowchart LR'];

  for (const node of graph.nodes) {
    const label = mermaidLabel(node.name);
    // Alvo externo, recurso ou não resolvido ganha outra forma:
    if (node.is_resource) {
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
    `  classDef padrao fill:${p.surface2},stroke:${p.line},stroke-width:1px,color:${p.txt}`,
    `  classDef raiz fill:${p.surface3},stroke:${p.visor},stroke-width:2.5px,color:${p.txt}`,
    `  classDef fora fill:${p.surface},stroke:${p.line},stroke-width:1px,color:${p.txtDim},stroke-dasharray: 5 4`,
    `  classDef fantasma fill:${p.surface},stroke:${p.crest},stroke-width:1.5px,color:${p.crest},stroke-dasharray: 4 3`,
    `  classDef depreciado fill:${p.surface2},stroke:${p.alert},stroke-width:1.5px,color:${p.alert}`,
    `  classDef externo fill:${p.surface3},stroke:${p.ok},stroke-width:2px,color:${p.ok}`,
    `  classDef recurso fill:${p.surface3},stroke:${p.visor},stroke-width:2px,color:${p.visor}`
  );

  const grouped = new Map<string, string[]>();
  for (const node of graph.nodes) {
    const cls = nodeClass(node);
    grouped.set(cls, [...(grouped.get(cls) || []), node.id]);
  }
  for (const [cls, ids] of grouped) {
    lines.push(`  class ${ids.join(',')} ${cls}`);
  }

  // Arestas de ciclo em destaque: é o achado que a tela existe para mostrar.
  graph.edges.forEach((edge, index) => {
    if (edge.in_cycle) {
      lines.push(`  linkStyle ${index} stroke:${p.alert},stroke-width:2px`);
    }
  });

  return lines.join('\n');
}
