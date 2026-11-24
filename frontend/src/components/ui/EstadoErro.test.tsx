import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { EstadoErro } from './index';

describe('EstadoErro', () => {
  it('"Tentar de novo" mostra que está tentando, em vez de parecer travado', () => {
    const onTentar = vi.fn();
    const { rerender } = render(<EstadoErro onTentar={onTentar} />);
    expect(screen.getByRole('button', { name: 'Tentar de novo' })).toBeEnabled();
    rerender(<EstadoErro onTentar={onTentar} tentando />);
    const botao = screen.getByRole('button', { name: 'Tentando…' });
    expect(botao).toBeDisabled();
    expect(botao).toHaveAttribute('aria-busy', 'true');
  });
});
