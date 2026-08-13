import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		port: 5173,
		// Só vale em `npm run dev`. Em produção o FastAPI serve o build e a API na
		// mesma origem, então `/api` já resolve sozinho — não há proxy nenhum.
		proxy: {
			'/api': {
				target: process.env.API_URL || 'http://localhost:8000',
				changeOrigin: true
			}
		}
	}
});
