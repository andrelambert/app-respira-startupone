/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: { port: 5173, strictPort: true },
  build: {
    target: 'es2020',
    // Orçamento de bundle inicial < 250 KB gzip (docs/contexto-produto.md §6.5): Recharts fica
    // fora do chunk inicial, carregado só nas rotas que desenham gráfico.
    chunkSizeWarningLimit: 400, // minificado; o orçamento é sobre gzip (≈150 KB no carregamento inicial)
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
});
