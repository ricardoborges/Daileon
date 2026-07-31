import { writable, get } from 'svelte/store';
import { browser } from '$app/environment';

export interface User {
  username: string;
  name: string;
  email?: string;
  is_admin: boolean;
  auth_type: 'break_glass' | 'ldap';
}

export interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  error: string | null;
}

const TOKEN_KEY = 'daileon_auth_token';

function createAuthStore() {
  const { subscribe, set, update } = writable<AuthState>({
    user: null,
    token: browser ? localStorage.getItem(TOKEN_KEY) : null,
    loading: true,
    error: null
  });

  return {
    subscribe,
    init: async () => {
      if (!browser) return;
      const token = localStorage.getItem(TOKEN_KEY);
      if (!token) {
        update(s => ({ ...s, user: null, token: null, loading: false }));
        return;
      }
      try {
        const res = await fetch('/api/auth/me', {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const user = await res.json();
          update(s => ({ ...s, user, token, loading: false, error: null }));
        } else {
          localStorage.removeItem(TOKEN_KEY);
          update(s => ({ ...s, user: null, token: null, loading: false }));
        }
      } catch (e) {
        localStorage.removeItem(TOKEN_KEY);
        update(s => ({ ...s, user: null, token: null, loading: false }));
      }
    },
    login: async (username: string, password: str) => {
      update(s => ({ ...s, loading: true, error: null }));
      try {
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password })
        });
        const data = await res.json();
        if (!res.ok) {
          const errorMsg = data.detail || 'Falha ao autenticar';
          update(s => ({ ...s, loading: false, error: errorMsg }));
          return false;
        }
        
        if (browser) {
          localStorage.setItem(TOKEN_KEY, data.access_token);
        }
        update(s => ({
          ...s,
          user: data.user,
          token: data.access_token,
          loading: false,
          error: null
        }));
        return true;
      } catch (e: any) {
        const errorMsg = e.message || 'Erro de conexão com o servidor';
        update(s => ({ ...s, loading: false, error: errorMsg }));
        return false;
      }
    },
    logout: () => {
      if (browser) {
        localStorage.removeItem(TOKEN_KEY);
      }
      set({ user: null, token: null, loading: false, error: null });
    }
  };
}

export const auth = createAuthStore();

export function getAuthHeader(): Record<string, string> {
  if (!browser) return {};
  const token = localStorage.getItem(TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}
