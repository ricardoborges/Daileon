import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		port: 5173
	}
	// As chamadas a /api são encaminhadas ao FastAPI pela rota
	// src/routes/api/[...path]/+server.ts (funciona em dev e em produção).
	// O destino vem da variável de ambiente API_URL.
});
