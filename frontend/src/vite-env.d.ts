/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  /** F5: copiloto em linguagem natural — desligado até existir de verdade (docs/contexto-produto.md §4). */
  readonly VITE_FEATURE_COPILOTO?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
