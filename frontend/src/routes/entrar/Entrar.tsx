import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router';
import { z } from 'zod';

import { BotaoVerSenha, Button, Campo, Card, Carregando, Icone } from '@/components/ui';
import { chaves, useConfig, useUsuario } from '@/hooks/queries';
import { api, ApiError, type Usuario } from '@/lib/api';
import { entrar as copy, erroConexao } from '@/lib/copy';
import { comMascara, semEspacos } from '@/lib/entrada';

const esquema = z.object({
  email: z.string().trim().email(copy.erros.email),
  senha: z.string().min(1, copy.erros.senha),
});
type Dados = z.infer<typeof esquema>;

/** Só volta para caminhos internos — nunca para uma URL externa vinda da query. */
function destinoSeguro(volta: string | null): string {
  return volta && volta.startsWith('/') && !volta.startsWith('//') ? volta : '/inicio';
}

export default function Entrar() {
  const { data: usuario, isLoading } = useUsuario();
  const { data: config } = useConfig();
  const [params] = useSearchParams();
  const destino = destinoSeguro(params.get('volta'));
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [verSenha, setVerSenha] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<Dados>({ resolver: zodResolver(esquema), defaultValues: { email: '', senha: '' } });

  const aoEntrar = (u: Usuario) => {
    qc.clear(); // nada do usuário anterior fica em cache
    qc.setQueryData(chaves.usuario, u);
    navigate(destino, { replace: true });
  };
  const login = useMutation({ mutationFn: (d: Dados) => api.entrar(d.email, d.senha), onSuccess: aoEntrar });
  const demo = useMutation({ mutationFn: api.entrarDemo, onSuccess: aoEntrar });

  if (isLoading) return <Carregando />;
  if (usuario) return <Navigate to={destino} replace />;

  const erro = login.error instanceof ApiError ? login.error.codigo : login.error ? 'padrao' : null;

  return (
    <div className="flex flex-col gap-6 pt-4">
      <form onSubmit={handleSubmit((d) => login.mutate(d))} className="flex flex-col gap-4" noValidate>
        <h1 className="text-3xl font-bold text-navy">{copy.titulo}</h1>
        <Campo
          rotulo={copy.email}
          type="email"
          autoComplete="email"
          inputMode="email"
          autoCapitalize="none"
          spellCheck={false}
          erro={errors.email?.message}
          {...comMascara(register('email'), semEspacos)}
        />
        <Campo
          rotulo={copy.senha}
          type={verSenha ? 'text' : 'password'}
          autoComplete="current-password"
          maxLength={128}
          erro={errors.senha?.message}
          sufixo={<BotaoVerSenha visivel={verSenha} onAlternar={() => setVerSenha((v) => !v)} />}
          {...register('senha')}
        />
        {erro && (
          <p role="alert" className="flex items-center gap-2 text-sm text-rose-ink">
            {Icone.alerta}
            {copy.erros[erro] ?? erroConexao(erro)}
          </p>
        )}
        <Button type="submit" largo disabled={login.isPending}>
          {copy.enviar}
        </Button>
        <p className="text-center text-sm text-slate">
          {copy.semConta}{' '}
          <Link to="/cadastro" className="font-semibold text-blue underline">
            {copy.criar}
          </Link>
        </p>
      </form>

      {config?.demo_disponivel && (
        <Card as="div" className="flex flex-col gap-2 border-dashed">
          <h2 className="font-semibold text-navy">{copy.demoTitulo}</h2>
          <p className="text-sm text-slate">{copy.demoTexto}</p>
          <Button variante="secundario" onClick={() => demo.mutate()} disabled={demo.isPending}>
            {copy.demo}
          </Button>
        </Card>
      )}
    </div>
  );
}
