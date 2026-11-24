import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Suspense } from 'react';
import { Link, Navigate, NavLink, Outlet, ScrollRestoration, useLocation, useNavigate } from 'react-router';

import { Badge, Carregando, cx } from '@/components/ui';
import { useUsuario } from '@/hooks/queries';
import { useOnline } from '@/hooks/useOnline';
import { api } from '@/lib/api';
import { conta, estados, marca, nav } from '@/lib/copy';

/** Rotas com dado financeiro: só com sessão. Sem ela, vai para /entrar e volta depois. */
export function ExigeLogin() {
  const { data: usuario, isLoading } = useUsuario();
  const local = useLocation();
  if (isLoading) return <Carregando />;
  if (!usuario) {
    const volta = encodeURIComponent(local.pathname + local.search);
    return <Navigate to={`/entrar?volta=${volta}`} replace />;
  }
  return <Outlet />;
}

function MenuConta() {
  const { data: usuario } = useUsuario();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const sair = useMutation({
    mutationFn: api.sair,
    onSettled: () => {
      qc.clear();
      navigate('/entrar', { replace: true });
    },
  });
  if (!usuario) return null;
  return (
    <div className="ml-auto flex items-center gap-3">
      {usuario.demo && <Badge tom="estimada">{conta.demo}</Badge>}
      <span className="hidden text-sm text-slate sm:inline">{usuario.apelido}</span>
      <button
        type="button"
        onClick={() => sair.mutate()}
        disabled={sair.isPending}
        className="min-h-toque px-2 text-sm font-semibold text-blue"
      >
        {conta.sair}
      </button>
    </div>
  );
}

function Logo() {
  return (
    <Link to="/" className="flex min-h-toque items-center gap-2 font-bold text-navy" aria-label="Respira — início">
      <img src="/icon.svg" alt="" width={28} height={28} />
      {marca.nome}
    </Link>
  );
}

function AvisoOffline() {
  const online = useOnline();
  if (online) return null;
  return (
    <p role="status" className="bg-amber-soft px-4 py-2 text-center text-sm text-amber-ink">
      {estados.offline}
    </p>
  );
}

/** Telas da jornada pós-cadastro: cabeçalho + navegação inferior (mobile-first). */
export function LayoutApp() {
  const itens = [
    { to: '/inicio', rotulo: nav.inicio },
    { to: '/contas', rotulo: nav.contas },
    { to: '/raiox', rotulo: nav.raiox },
    { to: '/dividas', rotulo: nav.dividas },
    { to: '/plano', rotulo: nav.plano },
    { to: '/configuracoes', rotulo: nav.configuracoes },
  ];
  return (
    <div className="min-h-dvh bg-light pb-24">
      <AvisoOffline />
      <header className="sticky top-0 z-10 border-b border-line bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-lg items-center px-4">
          <Logo />
          <MenuConta />
        </div>
      </header>
      <main className="mx-auto max-w-lg px-4 py-5">
        <Suspense fallback={<Carregando />}>
          <Outlet />
        </Suspense>
      </main>
      <nav aria-label="Principal" className="fixed inset-x-0 bottom-0 z-10 border-t border-line bg-white">
        {/* Largura pelo conteúdo: "Configurações" não cabe numa coluna de 1/6 em 360 px. */}
        <ul className="mx-auto flex max-w-lg justify-around px-1">
          {itens.map((i) => (
            <li key={i.to}>
              <NavLink
                to={i.to}
                className={({ isActive }) =>
                  cx(
                    'flex min-h-14 items-center justify-center whitespace-nowrap px-1 text-[13px] font-semibold sm:px-1.5 sm:text-sm',
                    isActive ? 'text-blue' : 'text-slate',
                  )
                }
              >
                {i.rotulo}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <ScrollRestoration />
    </div>
  );
}

/** Landing, cadastro, conexão e callbacks: sem navegação, foco na tarefa. */
export function LayoutSimples() {
  return (
    <div className="min-h-dvh bg-light">
      <AvisoOffline />
      <header className="mx-auto flex max-w-lg items-center px-4 pt-2">
        <Logo />
        <MenuConta />
      </header>
      <main className="mx-auto max-w-lg px-4 pb-10 pt-3">
        <Suspense fallback={<Carregando />}>
          <Outlet />
        </Suspense>
      </main>
      <ScrollRestoration />
    </div>
  );
}
