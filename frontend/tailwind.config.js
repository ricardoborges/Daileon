/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Space Grotesk', 'Segoe UI', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Consolas', 'monospace'],
      },
      colors: {
        /* Armadura — neutro frio de aço, base de todas as superfícies */
        steel: {
          50: '#f4f6f7',
          100: '#e6eaec',
          200: '#c8d2d7',
          300: '#a2b0b8',
          400: '#6e7f89',
          500: '#4d5d67',
          600: '#3a464e',
          700: '#2b343a',
          800: '#1b252b',
          850: '#141c21',
          900: '#0f1519',
          950: '#080c0f',
        },
        /* Visor — ciano de ação e foco */
        visor: {
          300: '#7ce9fb',
          400: '#2ed3ec',
          500: '#12b0cd',
          600: '#0a7f99',
          700: '#0c6479',
          900: '#07333f',
        },
        /* Crista — ouro de destaque e hierarquia */
        crest: {
          300: '#f5d67e',
          400: '#e9b93f',
          500: '#c9930f',
          600: '#9a6f06',
          900: '#3f2c05',
        },
        /* Asas — vermelho de alerta */
        alert: {
          400: '#f4634a',
          500: '#e04128',
          600: '#c53a24',
        },
      },
      borderRadius: {
        DEFAULT: '2px',
        sm: '2px',
        md: '3px',
        lg: '3px',
        xl: '4px',
      },
      keyframes: {
        scan: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
        sweep: {
          '0%': { transform: 'translateY(-2rem)', opacity: '0' },
          '35%': { opacity: '1' },
          '100%': { transform: 'translateY(22rem)', opacity: '0' },
        },
      },
      animation: {
        scan: 'scan 1.6s linear infinite',
        sweep: 'sweep 7s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
