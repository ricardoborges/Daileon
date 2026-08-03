import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';

/** Preserva os links de detalhe de domínio salvos antes da mudança de rota. */
export const load: PageLoad = ({ params }) => {
  redirect(308, `/catalog/domains/${encodeURIComponent(params.name)}`);
};
