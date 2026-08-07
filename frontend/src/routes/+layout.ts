/**
 * O portal é uma SPA: todo dado vem de `fetch` no cliente, autenticado com o
 * token guardado no navegador (`$lib/auth`). Não há nada para renderizar no
 * servidor antes do login, então SSR e prerender ficam desligados — é o que
 * permite o `adapter-static` gerar apenas o `index.html` de fallback.
 */
export const ssr = false;
export const prerender = false;
