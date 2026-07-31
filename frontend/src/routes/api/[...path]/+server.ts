import { env } from '$env/dynamic/private';
import type { RequestHandler } from './$types';

/**
 * Proxy de API do lado do servidor.
 *
 * O navegador sempre fala com a própria origem (`/api/...`) e é este servidor
 * SvelteKit que encaminha para o FastAPI. Isso mantém o mesmo comportamento em
 * dev e em produção (adapter-node / Docker), dispensa CORS e permite usar o
 * hostname interno da rede Docker (`http://backend:8000`), que o navegador não
 * conseguiria resolver.
 *
 * Configuração: variável de ambiente `API_URL` lida em runtime.
 */
const target = (env.API_URL || 'http://localhost:8000').replace(/\/$/, '');

const proxy: RequestHandler = async ({ request, url, fetch }) => {
  // `url.pathname` preserva a codificação original — importante para os
  // caminhos de documento (ex.: `docs/guia%2Fintro.md`).
  const upstream = `${target}${url.pathname}${url.search}`;

  const headers = new Headers();
  const accept = request.headers.get('accept');
  const contentType = request.headers.get('content-type');
  const authorization = request.headers.get('authorization');
  if (accept) headers.set('accept', accept);
  if (contentType) headers.set('content-type', contentType);
  if (authorization) headers.set('authorization', authorization);


  const hasBody = !['GET', 'HEAD'].includes(request.method);

  try {
    const res = await fetch(upstream, {
      method: request.method,
      headers,
      body: hasBody ? await request.arrayBuffer() : undefined
    });

    return new Response(res.body, {
      status: res.status,
      headers: {
        'content-type': res.headers.get('content-type') ?? 'application/json'
      }
    });
  } catch (e) {
    console.error(`[api-proxy] falha ao contatar ${upstream}:`, e);
    return new Response(
      JSON.stringify({ detail: `Backend indisponível em ${target}` }),
      { status: 502, headers: { 'content-type': 'application/json' } }
    );
  }
};

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
