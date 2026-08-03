import type { ParamMatcher } from '@sveltejs/kit';

/**
 * Restringe `/catalog/[id]` a IDs numéricos.
 *
 * Sem isso, `/catalog/solutions` casaria com a rota de detalhe do projeto e o
 * componente tentaria carregar o id `"solutions"`.
 */
export const match: ParamMatcher = (param) => /^\d+$/.test(param);
