import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';

import type { Vencimento } from '@/lib/api';
import { vencimentos as copy } from '@/lib/copy';
import { centavos } from '@/lib/money';

import { ListaVencimentos } from './ListaVencimentos';

const base: Vencimento = {
  data: '2026-12-12',
  tipo: 'FATURA',
  credor: 'Nubank',
  descricao: 'Nubank Mastercard',
  valor: centavos(20800),
  valor_total: centavos(208000),
  valor_plano: null,
  status: 'PENDENTE',
  dias: 19,
  divida_id: 7,
  conta_id: 4,
  banco_logo: null,
};

const nbsp = (s: string | null) => (s ?? '').replace(/[\u00a0\u202f]/g, ' ');

describe('ListaVencimentos (N3)', () => {
  it('status com rótulo escrito (nunca só cor), valor e quanto falta da fatura', () => {
    render(
      <MemoryRouter>
        <ListaVencimentos
          itens={[
            base,
            { ...base, tipo: 'PARCELA', descricao: 'Carnê Loja D', status: 'ATRASADO', dias: -12, conta_id: null, valor: centavos(9500), valor_total: null },
          ]}
        />
      </MemoryRouter>,
    );
    expect(screen.getByText('Pendente')).toBeInTheDocument();
    expect(screen.getByText('Atrasado')).toBeInTheDocument();
    expect(screen.getByText(/venceu há 12 dias/)).toBeInTheDocument();
    expect(nbsp(document.body.textContent)).toContain('de R$ 2.080,00 da fatura');
    expect(screen.getByRole('link', { name: /Nubank Mastercard/ })).toHaveAttribute('href', '/contas/4');
  });

  it('valor do plano só aparece quando existe', () => {
    const { rerender } = render(
      <MemoryRouter>
        <ListaVencimentos itens={[base]} />
      </MemoryRouter>,
    );
    expect(screen.queryByText(/no plano/)).not.toBeInTheDocument();
    rerender(
      <MemoryRouter>
        <ListaVencimentos itens={[{ ...base, valor_plano: centavos(20800) }, { ...base, data: '2026-12-13', valor_plano: centavos(51386) }]} />
      </MemoryRouter>,
    );
    expect(nbsp(screen.getByText(/no plano/).textContent)).toBe('no plano: R$ 513,86');
  });

  it('textos de prazo', () => {
    expect(copy.quando(0)).toBe('vence hoje');
    expect(copy.quando(1)).toBe('vence amanhã');
    expect(copy.quando(-1)).toBe('venceu há 1 dia');
  });
});
