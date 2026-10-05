import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import Cadastro from './Cadastro';

function montar() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Cadastro />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  // Ninguém logado: /usuarios/me → 401.
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(JSON.stringify({ detail: 'nao_autenticado' }), { status: 401 })),
  );
});

const campo = (rotulo: RegExp) => screen.getByLabelText(rotulo) as HTMLInputElement;
const verde = (el: HTMLElement) => el.className.includes('border-green') && !el.hasAttribute('aria-invalid');
const vermelho = (el: HTMLElement) => el.className.includes('border-rose') && el.getAttribute('aria-invalid') === 'true';
const neutro = (el: HTMLElement) => el.className.includes('border-line') && !el.hasAttribute('aria-invalid');

describe('cadastro — validação inline', () => {
  it('e-mail não aceita espaço e exige @dominio.tld', async () => {
    montar();
    const u = userEvent.setup();
    const email = await waitFor(() => campo(/e-mail/i));
    await u.type(email, 'andre @gmail');
    expect(email.value).toBe('andre@gmail');
    expect(vermelho(email)).toBe(true);
    expect(screen.getByText(/nome@dominio\.com/)).toBeInTheDocument();
    await u.type(email, '.com');
    expect(verde(email)).toBe(true);
    await u.tab(); // saiu do campo: volta ao neutro
    expect(neutro(email)).toBe(true);
  });

  it('senha fica verde só com 8 caracteres, dizendo quantos faltam', async () => {
    montar();
    const u = userEvent.setup();
    const senha = await waitFor(() => campo(/crie uma senha/i));
    await u.type(senha, '1234567');
    expect(vermelho(senha)).toBe(true);
    expect(screen.getByText('Faltam 1 caractere.')).toBeInTheDocument();
    await u.type(senha, '8');
    expect(verde(senha)).toBe(true);
    await u.click(screen.getByRole('button', { name: /mostrar senha/i }));
    expect(senha.type).toBe('text');
  });

  it('CPF só aceita número, formata sozinho e valida os dígitos', async () => {
    montar();
    const u = userEvent.setup();
    const cpf = await waitFor(() => campo(/^cpf/i));
    await u.type(cpf, 'ab529982247');
    expect(cpf.value).toBe('529.982.247');
    expect(screen.getByText('Faltam 2 dígitos.')).toBeInTheDocument();
    await u.type(cpf, '24');
    expect(cpf.value).toBe('529.982.247-24');
    expect(vermelho(cpf)).toBe(true);
    expect(screen.getByText(/CPF não é válido/)).toBeInTheDocument();
    await u.type(cpf, '{Backspace}5');
    expect(cpf.value).toBe('529.982.247-25');
    expect(verde(cpf)).toBe(true);
  });

  it('letra no meio do CPF não come o dígito seguinte', async () => {
    montar();
    const u = userEvent.setup();
    const cpf = await waitFor(() => campo(/^cpf/i));
    await u.type(cpf, 'abc5299822472x5');
    expect(cpf.value).toBe('529.982.247-25');
  });

  it('ao enviar vazio, o que falta fica vermelho mesmo fora de foco', async () => {
    montar();
    const u = userEvent.setup();
    await waitFor(() => campo(/e-mail/i));
    await u.click(screen.getByRole('button', { name: 'Criar conta' }));
    await waitFor(() => expect(vermelho(campo(/e-mail/i))).toBe(true));
    expect(vermelho(campo(/^cpf/i))).toBe(true);
    expect(vermelho(campo(/nome completo/i))).toBe(true);
  });
});
