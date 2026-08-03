import type { DocFileItem } from '$lib/api';

export interface DocTreeFile {
  kind: 'file';
  /** Nome exibido — o título vindo da API, sem o caminho. */
  name: string;
  path: string;
  doc: DocFileItem;
}

export interface DocTreeFolder {
  kind: 'folder';
  name: string;
  /** Caminho do diretório, usado como chave de expansão. */
  path: string;
  children: DocTreeNode[];
}

export type DocTreeNode = DocTreeFile | DocTreeFolder;

/** Documentos que abrem a seção em que estão e por isso vêm primeiro. */
const ENTRY_POINTS = ['index.md', 'index.markdown', 'readme.md'];

function entryRank(fileName: string): number {
  const idx = ENTRY_POINTS.indexOf(fileName.toLowerCase());
  return idx === -1 ? ENTRY_POINTS.length : idx;
}

function compareNodes(a: DocTreeNode, b: DocTreeNode): number {
  // Pastas antes de arquivos: a lista fica com a estrutura visível no topo,
  // em vez de diretórios perdidos no meio dos documentos.
  if (a.kind !== b.kind) return a.kind === 'folder' ? -1 : 1;

  if (a.kind === 'file' && b.kind === 'file') {
    const rank = entryRank(a.path.split('/').pop() || '') - entryRank(b.path.split('/').pop() || '');
    if (rank !== 0) return rank;
  }

  return a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' });
}

function sortTree(nodes: DocTreeNode[]): DocTreeNode[] {
  nodes.sort(compareNodes);
  for (const node of nodes) {
    if (node.kind === 'folder') sortTree(node.children);
  }
  return nodes;
}

/**
 * Converte a lista plana de `relative_path` na árvore de diretórios do
 * repositório. `docs/NTI-001 SIMBA/guia.md` vira a pasta `NTI-001 SIMBA`
 * contendo `guia.md`.
 */
export function buildDocsTree(docs: DocFileItem[]): DocTreeNode[] {
  const roots: DocTreeNode[] = [];
  const folders = new Map<string, DocTreeFolder>();

  for (const doc of docs) {
    const segments = doc.relative_path.split('/').filter(Boolean);
    if (segments.length === 0) continue;

    const fileName = segments.pop() as string;
    let siblings = roots;
    let prefix = '';

    for (const segment of segments) {
      prefix = prefix ? `${prefix}/${segment}` : segment;
      let folder = folders.get(prefix);
      if (!folder) {
        folder = { kind: 'folder', name: segment, path: prefix, children: [] };
        folders.set(prefix, folder);
        siblings.push(folder);
      }
      siblings = folder.children;
    }

    siblings.push({
      kind: 'file',
      name: doc.title || fileName,
      path: doc.relative_path,
      doc
    });
  }

  return sortTree(roots);
}

/** Caminhos de todas as pastas ancestrais de `docPath`. */
export function ancestorFolders(docPath: string): string[] {
  const segments = docPath.split('/').filter(Boolean);
  segments.pop();
  const paths: string[] = [];
  let prefix = '';
  for (const segment of segments) {
    prefix = prefix ? `${prefix}/${segment}` : segment;
    paths.push(prefix);
  }
  return paths;
}

/** Todos os caminhos de pasta da árvore, para "expandir tudo". */
export function allFolderPaths(nodes: DocTreeNode[]): string[] {
  const paths: string[] = [];
  const walk = (list: DocTreeNode[]) => {
    for (const node of list) {
      if (node.kind === 'folder') {
        paths.push(node.path);
        walk(node.children);
      }
    }
  };
  walk(nodes);
  return paths;
}

/**
 * Documento a abrir quando nenhum foi pedido. Um arquivo do nível atual vem
 * antes de descer nas pastas: como a ordenação já joga `index.md`/`README.md`
 * para o topo, isso escolhe o ponto de entrada em vez de um anexo qualquer.
 */
export function firstDocPath(nodes: DocTreeNode[]): string | null {
  const file = nodes.find((n): n is DocTreeFile => n.kind === 'file');
  if (file) return file.path;

  for (const node of nodes) {
    if (node.kind === 'folder') {
      const nested = firstDocPath(node.children);
      if (nested) return nested;
    }
  }
  return null;
}

/**
 * Resolve um caminho relativo escrito dentro de `fromDocPath` — a referência de
 * uma imagem no Markdown, por exemplo — contra a pasta desse documento.
 * `resolveDocPath('a/b/guia.md', '../img/x.png')` → `a/img/x.png`.
 */
export function resolveDocPath(fromDocPath: string, relative: string): string {
  const segments = fromDocPath.split('/').slice(0, -1);
  for (const segment of relative.split('/')) {
    if (!segment || segment === '.') continue;
    if (segment === '..') segments.pop();
    else segments.push(segment);
  }
  return segments.join('/');
}

export function formatDocSize(bytes?: number | null): string {
  if (bytes === null || bytes === undefined) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
