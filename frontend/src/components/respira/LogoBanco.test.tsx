import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { LogoBanco } from './index';

describe('LogoBanco', () => {
  it('usa a imagem do catálogo, sem vazar a URL da página (referrer)', () => {
    const { container } = render(<LogoBanco nome="Nubank" logo="https://statics.belvo.io/nubank.svg" />);
    const img = container.querySelector('img')!;
    expect(img.getAttribute('src')).toBe('https://statics.belvo.io/nubank.svg');
    expect(img.getAttribute('referrerpolicy')).toBe('no-referrer');
    expect(img.getAttribute('alt')).toBe(''); // decorativo: o nome está escrito ao lado
  });

  it('sem logo, ou se a imagem falhar, mostra as iniciais', () => {
    render(<LogoBanco nome="Banco do Brasil" logo={null} />);
    expect(screen.getByText('BD')).toBeInTheDocument();
    const { container } = render(<LogoBanco nome="Nubank" logo="https://statics.belvo.io/quebrado.svg" />);
    fireEvent.error(container.querySelector('img')!);
    expect(screen.getByText('N')).toBeInTheDocument();
  });
});
