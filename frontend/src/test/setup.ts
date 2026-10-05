import '@testing-library/jest-dom/vitest';

import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

// Sem `globals` no Vitest, o Testing Library não desmonta sozinho entre testes.
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
