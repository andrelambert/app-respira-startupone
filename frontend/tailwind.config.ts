import type { Config } from 'tailwindcss';

/**
 * Tokens do design system (docs/contexto-produto.md §10) — a mesma identidade dos diagramas e
 * slides da Fase 5. Carregado pelo Tailwind v4 via `@config` em src/index.css.
 */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: '#12314F', // títulos, telas escuras
        ink: '#1E293B', // texto corrido
        slate: '#64748B', // secundário, legendas
        line: '#E2E8F0', // bordas, divisores
        light: '#F8FAFC', // fundo de seções
        blue: { DEFAULT: '#2563EB', soft: '#F5F9FF' }, // ação primária
        purple: { DEFAULT: '#7C3AED', soft: '#FAF8FF' }, // estratégia / plano
        green: { DEFAULT: '#059669', soft: '#F4FDF8', ink: '#047857' }, // progresso, quitada, economia (ink = texto, 4.5:1)
        amber: { DEFAULT: '#D97706', soft: '#FFFCF3', ink: '#92400E' }, // atenção, estimativa
        rose: { DEFAULT: '#E11D48', soft: '#FFF7F8', ink: '#9F1239' }, // só FATOS de custo alto
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', '"Segoe UI"', 'Roboto', 'sans-serif'],
      },
      minHeight: { toque: '44px' },
      minWidth: { toque: '44px' },
    },
  },
} satisfies Config;
