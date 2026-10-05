import './index.css';

import { QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { createBrowserRouter, Navigate, RouterProvider } from 'react-router';

import { ExigeLogin, LayoutApp, LayoutSimples } from '@/components/Layout';
import { chaves } from '@/hooks/queries';
import { ApiError } from '@/lib/api';

const queryClient: QueryClient = new QueryClient({
  // Sessão expirou no meio do uso: zera o usuário e o guard leva para /entrar.
  queryCache: new QueryCache({
    onError: (erro) => {
      if (erro instanceof ApiError && erro.status === 401) queryClient.setQueryData(chaves.usuario, null);
    },
  }),
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (falhas, erro) => !(erro instanceof ApiError && erro.status >= 400 && erro.status < 500) && falhas < 2,
      // Plano de dados limitado: não refaz busca só porque a aba ganhou foco.
      refetchOnWindowFocus: false,
    },
  },
});

// Code splitting por rota (docs/contexto-produto.md §6.5): cada tela é um chunk.
const tela = (carregar: () => Promise<{ default: React.ComponentType }>) => async () => ({
  Component: (await carregar()).default,
});

const router = createBrowserRouter([
  {
    element: <LayoutSimples />,
    children: [
      { path: '/', lazy: tela(() => import('@/routes/landing/Landing')) },
      { path: '/entrar', lazy: tela(() => import('@/routes/entrar/Entrar')) },
      { path: '/cadastro', lazy: tela(() => import('@/routes/cadastro/Cadastro')) },
      {
        element: <ExigeLogin />,
        children: [
          { path: '/conectar', lazy: tela(() => import('@/routes/conectar/Conectar')) },
          { path: '/conectar/sucesso', lazy: tela(() => import('@/routes/conectar/Sucesso')) },
          { path: '/conectar/saida', lazy: tela(() => import('@/routes/conectar/Saida')) },
          { path: '/conectar/evento', lazy: tela(() => import('@/routes/conectar/Evento')) },
          { path: '/conectar/simulado', lazy: tela(() => import('@/routes/conectar/WidgetSimulado')) },
        ],
      },
    ],
  },
  {
    element: <LayoutApp />,
    children: [
      {
        element: <ExigeLogin />,
        children: [
          { path: '/inicio', lazy: tela(() => import('@/routes/inicio/Inicio')) },
          { path: '/contas', lazy: tela(() => import('@/routes/contas/Contas')) },
          { path: '/contas/:id', lazy: tela(() => import('@/routes/contas/ContaDetalhe')) },
          { path: '/raiox', lazy: tela(() => import('@/routes/raiox/RaioX')) },
          { path: '/plano', lazy: tela(() => import('@/routes/plano/Plano')) },
          { path: '/configuracoes', lazy: tela(() => import('@/routes/configuracoes/Configuracoes')) },
          // endereço antigo continua funcionando
          { path: '/privacidade', element: <Navigate to="/configuracoes" replace /> },
          { path: '/dividas/nova', lazy: tela(() => import('@/routes/dividas/NovaDivida')) },
          { path: '/dividas/:id', lazy: tela(() => import('@/routes/dividas/ConferirDivida')) },
          { path: '/licoes/:slug', lazy: tela(() => import('@/routes/licoes/Licao')) },
        ],
      },
      { path: '*', lazy: tela(() => import('@/routes/NaoEncontrada')) },
    ],
  },
]);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
);
