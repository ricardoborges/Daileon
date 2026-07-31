import { writable } from 'svelte/store';

type Theme = 'light' | 'dark';

const initialTheme: Theme = (typeof window !== 'undefined' && localStorage.getItem('daileon_theme') as Theme) || 'dark';

export const theme = writable<Theme>(initialTheme);

export function toggleTheme() {
  theme.update((current) => {
    const next = current === 'dark' ? 'light' : 'dark';
    if (typeof window !== 'undefined') {
      localStorage.setItem('daileon_theme', next);
      if (next === 'dark') {
        document.documentElement.classList.add('dark');
        document.documentElement.classList.remove('light');
      } else {
        document.documentElement.classList.remove('dark');
        document.documentElement.classList.add('light');
      }
    }
    return next;
  });
}

export function initTheme() {
  if (typeof window === 'undefined') return;
  const saved = (localStorage.getItem('daileon_theme') as Theme) || 'dark';
  theme.set(saved);
  if (saved === 'dark') {
    document.documentElement.classList.add('dark');
    document.documentElement.classList.remove('light');
  } else {
    document.documentElement.classList.remove('dark');
    document.documentElement.classList.add('light');
  }
}
