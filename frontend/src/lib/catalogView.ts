/** Estado compartilhado das listagens do catálogo (aba e modo de visão). */

export type CatalogEntity = 'projects' | 'solutions' | 'domains';
export type ViewMode = 'cards' | 'table';

export const CATALOG_ENTITIES: CatalogEntity[] = ['projects', 'solutions', 'domains'];

const LAST_ENTITY_KEY = 'daileon_catalog_entity';
const VIEW_MODE_KEY = 'daileon_view_mode';

export function isCatalogEntity(value: unknown): value is CatalogEntity {
  return typeof value === 'string' && (CATALOG_ENTITIES as string[]).includes(value);
}

/**
 * A aba vem da URL para o link ser compartilhável; o localStorage só decide
 * o padrão de quem chega em `/catalog` sem query.
 */
export function resolveEntity(param: string | null): CatalogEntity {
  if (isCatalogEntity(param)) return param;
  if (typeof window === 'undefined') return 'projects';
  const saved = localStorage.getItem(LAST_ENTITY_KEY);
  return isCatalogEntity(saved) ? saved : 'projects';
}

export function rememberEntity(entity: CatalogEntity) {
  if (typeof window !== 'undefined') {
    localStorage.setItem(LAST_ENTITY_KEY, entity);
  }
}

export function loadViewMode(entity: CatalogEntity): ViewMode {
  if (typeof window === 'undefined') return 'cards';
  const saved = localStorage.getItem(`${VIEW_MODE_KEY}:${entity}`);
  return saved === 'table' || saved === 'cards' ? saved : 'cards';
}

export function saveViewMode(entity: CatalogEntity, mode: ViewMode) {
  if (typeof window !== 'undefined') {
    localStorage.setItem(`${VIEW_MODE_KEY}:${entity}`, mode);
  }
}

/** Linha da tabela de grupos (domínios ou soluções). */
export interface GroupRow {
  name: string;
  href: string;
  crossValues: string[];
  owners: string[];
  componentsCount: number;
}

export function solutionHref(name: string): string {
  return `/catalog/solutions/${encodeURIComponent(name)}`;
}

export function domainHref(name: string): string {
  return `/catalog/domains/${encodeURIComponent(name)}`;
}
