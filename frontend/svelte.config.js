import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/**
 * O build é uma SPA estática servida pelo próprio FastAPI (ver `backend/main.py`).
 *
 * `fallback` é o que torna isso possível: um único `index.html` devolvido para
 * qualquer rota desconhecida, deixando o roteamento por conta do cliente. Sem
 * ele, um deep link como `/catalog/12/docs/guia.md` daria 404 no servidor.
 *
 * @type {import('@sveltejs/kit').Config}
 */
const config = {
	preprocess: vitePreprocess(),
	kit: {
		adapter: adapter({
			fallback: 'index.html',
			precompress: false
		})
	}
};

export default config;
