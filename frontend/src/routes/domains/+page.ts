import { redirect } from '@sveltejs/kit';

/** Domínios deixaram de ter menu próprio: agora são uma aba do catálogo. */
export function load() {
  redirect(308, '/catalog?tab=domains');
}
