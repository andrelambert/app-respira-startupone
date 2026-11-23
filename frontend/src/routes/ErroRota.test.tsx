import { render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ehFalhaDeChunk, podeRecarregar } from '@/lib/recarga';

import ErroRota from './ErroRota';

function Quebra(): never {
  throw new Error('qualquer falha de renderização');
}

function montar(lazyErro?: Error) {
  const router = createMemoryRouter([
    {
      errorElement: <ErroRota />,
      children: [
        lazyErro
          ? { path: '/', lazy: () => Promise.reject(lazyErro) }
          : { path: '/', element: <Quebra /> },
      ],
    },
  ]);
  return render(<RouterProvider router={router} />);
}

describe('ErroRota (A3)', () => {
  const reload = vi.fn();

  beforeEach(() => {
    sessionStorage.clear();
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.stubGlobal('location', { ...window.location, reload });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    reload.mockReset();
  });

  it('uma rota que lança erro mostra a tela própria, não a do React Router', async () => {
    montar();
    expect(await screen.findByText('Algo não carregou')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Recarregar' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ir para o Início' })).toHaveAttribute('href', '/inicio');
    expect(screen.queryByText(/Unexpected Application Error/i)).not.toBeInTheDocument();
    expect(reload).not.toHaveBeenCalled(); // erro comum não recarrega sozinho
  });

  it('chunk que não carregou recarrega a página uma vez só', async () => {
    montar(new TypeError('Failed to fetch dynamically imported module: /assets/Plano-abc.js'));
    await screen.findByText('Algo não carregou');
    expect(reload).toHaveBeenCalledTimes(1);
  });
});

describe('recarga', () => {
  beforeEach(() => sessionStorage.clear());

  it('reconhece as mensagens de chunk dos navegadores', () => {
    expect(ehFalhaDeChunk(new TypeError('Failed to fetch dynamically imported module: x'))).toBe(true);
    expect(ehFalhaDeChunk(new TypeError('Importing a module script failed.'))).toBe(true);
    expect(ehFalhaDeChunk(Object.assign(new Error('x'), { name: 'ChunkLoadError' }))).toBe(true);
    expect(ehFalhaDeChunk(new Error('outra coisa'))).toBe(false);
    expect(ehFalhaDeChunk('texto')).toBe(false);
  });

  it('não entra em laço: a segunda tentativa logo depois é recusada', () => {
    expect(podeRecarregar(1_000_000)).toBe(true);
    expect(podeRecarregar(1_005_000)).toBe(false);
    expect(podeRecarregar(1_000_000 + 31_000)).toBe(true); // bem depois, pode de novo
  });
});
