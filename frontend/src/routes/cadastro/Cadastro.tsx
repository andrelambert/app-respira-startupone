import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, Navigate } from 'react-router';
import { z } from 'zod';

import { NaoMovimenta } from '@/components/respira';
import { BotaoVerSenha, Button, Campo, Carregando, Icone, type EstadoCampo } from '@/components/ui';
import { chaves, useConfig, useUsuario } from '@/hooks/queries';
import { api, ApiError } from '@/lib/api';
import { cadastro, erroConexao } from '@/lib/copy';
import {
  comMascara,
  cpfValido,
  EMAIL_RE,
  formatarCpf,
  nomeCompletoValido,
  sanitizarNome,
  semEspacos,
  SENHA_MINIMO,
  somenteDigitos,
} from '@/lib/entrada';

/**
 * ``pedeCpf``: o CPF só serve para o banco confirmar a identidade na conexão
 * (§7.2). Sem a Belvo (versão pública), ele não é pedido — minimização (LGPD).
 */
const esquemaCadastro = (pedeCpf: boolean) =>
  z.object({
    email: z.string().max(254).regex(EMAIL_RE, cadastro.erros.email),
    senha: z.string().min(SENHA_MINIMO, cadastro.erros.senha).max(128),
    confirmar_senha: z.string().max(128),
    nome_completo: z.string().max(120).refine(nomeCompletoValido, cadastro.erros.nome),
    cpf: pedeCpf ? z.string().refine(cpfValido, cadastro.erros.cpf) : z.string().max(14),
    tentativa: z.enum(['sim', 'nao', 'pular']),
  }).refine((d) => d.confirmar_senha === d.senha, {
    path: ['confirmar_senha'],
    message: cadastro.erros.confirmarSenha,
    // O Zod 4 pula a checagem do objeto quando outro campo está inválido; esta roda sempre.
    when: (p) => typeof (p.value as { confirmar_senha?: unknown } | undefined)?.confirmar_senha === 'string',
  });
type Dados = z.infer<ReturnType<typeof esquemaCadastro>>;
type CampoTexto = Exclude<keyof Dados, 'tentativa'>;

/**
 * Etapa 2 — Cadastro (§9). Nenhum dado financeiro é pedido. Nome completo e
 * CPF são exigidos porque o banco confirma a identidade na autorização (§7.2).
 */
export default function Cadastro() {
  const { data: usuario, isLoading } = useUsuario();
  const config = useConfig();
  // Enquanto a configuração carrega, pede (o lado seguro); o backend decide no fim.
  const pedeCpf = config.data?.belvo_configurada ?? true;
  const qc = useQueryClient();
  const [foco, setFoco] = useState<CampoTexto | null>(null);
  const [verSenha, setVerSenha] = useState(false);
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitted },
  } = useForm<Dados>({
    resolver: zodResolver(esquemaCadastro(pedeCpf)),
    mode: 'onChange', // valida a cada tecla
    defaultValues: { email: '', senha: '', confirmar_senha: '', nome_completo: '', cpf: '', tentativa: 'pular' },
  });
  const criar = useMutation({
    mutationFn: (d: Dados) =>
      api.registrar({
        email: d.email,
        senha: d.senha,
        nome_completo: d.nome_completo.trim(),
        ...(pedeCpf ? { cpf: somenteDigitos(d.cpf) } : {}),
        ja_desistiu_de_plano: d.tentativa === 'pular' ? null : d.tentativa === 'sim',
      }),
    onSuccess: (u) => {
      qc.clear();
      qc.setQueryData(chaves.usuario, u);
    },
  });

  const senha = watch('senha');

  if (isLoading) return <Carregando />;
  // Logado ao chegar aqui → início. Logado porque acabou de criar a conta → conexão.
  if (usuario) return <Navigate to={criar.isSuccess ? '/conectar' : '/inicio'} replace />;

  /**
   * Verde/vermelho enquanto o cursor está no campo; ao sair, volta ao neutro.
   * Depois de tentar enviar, o que estiver errado fica vermelho mesmo fora de foco.
   */
  function estado(campo: CampoTexto): EstadoCampo {
    const valor = watch(campo);
    // A confirmação depende de outro campo: confere direto, não pelo último erro guardado.
    const erro = campo === 'confirmar_senha' ? valor !== senha : Boolean(errors[campo]);
    // Envio com erro foca o primeiro campo inválido: vazio, ele precisa aparecer vermelho.
    if (foco === campo) return valor ? (erro ? 'invalido' : 'valido') : isSubmitted && erro ? 'invalido' : 'neutro';
    return isSubmitted && erro ? 'invalido' : 'neutro';
  }

  /** register + rastreio de foco + máscara opcional. */
  function campo(nome: CampoTexto, mascara?: (v: string) => string) {
    const r = register(nome);
    const base = mascara ? comMascara(r, mascara) : r;
    return {
      ...base,
      onFocus: () => setFoco(nome),
      onBlur: (e: React.FocusEvent<HTMLInputElement>) => {
        setFoco(null);
        return r.onBlur(e);
      },
    };
  }

  const cpfDigitos = somenteDigitos(watch('cpf'));
  const mensagens: Record<CampoTexto, string | undefined> = {
    email: errors.email && cadastro.erros.email,
    senha:
      errors.senha &&
      (senha.length < SENHA_MINIMO ? cadastro.faltamCaracteres(SENHA_MINIMO - senha.length) : cadastro.erros.senha),
    confirmar_senha: estado('confirmar_senha') === 'invalido' ? cadastro.erros.confirmarSenha : undefined,
    nome_completo: errors.nome_completo && cadastro.erros.nome,
    cpf: errors.cpf && (cpfDigitos.length < 11 ? cadastro.faltamDigitos(11 - cpfDigitos.length) : cadastro.erros.cpf),
  };
  const erro = criar.error instanceof ApiError ? criar.error.codigo : criar.error ? 'padrao' : null;

  return (
    <form onSubmit={handleSubmit((d) => criar.mutate(d))} className="flex flex-col gap-3 pt-4" noValidate>
      <div className="mb-2">
        <h1 className="text-3xl font-bold text-navy">{cadastro.titulo}</h1>
        <p className="mt-1 text-slate">{cadastro.subtitulo}</p>
      </div>
      {/* Medo nº 1 da pesquisa (9 de 10) e do teste com conta real: dito antes de pedir qualquer dado. */}
      <NaoMovimenta />
      <Campo
        rotulo={cadastro.email}
        type="email"
        autoComplete="email"
        inputMode="email"
        autoCapitalize="none"
        spellCheck={false}
        estado={estado('email')}
        mensagem={mensagens.email}
        {...campo('email', semEspacos)}
      />
      <Campo
        rotulo={cadastro.senha}
        ajuda={cadastro.senhaAjuda}
        type={verSenha ? 'text' : 'password'}
        autoComplete="new-password"
        maxLength={128}
        estado={estado('senha')}
        mensagem={mensagens.senha}
        sufixo={<BotaoVerSenha visivel={verSenha} onAlternar={() => setVerSenha((v) => !v)} />}
        {...campo('senha')}
      />
      <Campo
        rotulo={cadastro.confirmarSenha}
        type={verSenha ? 'text' : 'password'}
        autoComplete="new-password"
        maxLength={128}
        estado={estado('confirmar_senha')}
        mensagem={mensagens.confirmar_senha}
        {...campo('confirmar_senha')}
      />
      <Campo
        rotulo={cadastro.nome}
        ajuda={cadastro.nomeAjuda}
        autoComplete="name"
        autoCapitalize="words"
        maxLength={120}
        estado={estado('nome_completo')}
        mensagem={mensagens.nome_completo}
        {...campo('nome_completo', sanitizarNome)}
      />
      {pedeCpf && (
        <Campo
          rotulo={cadastro.cpf}
          ajuda={cadastro.cpfAjuda}
          inputMode="numeric"
          autoComplete="off"
          placeholder="000.000.000-00"
          // Sem maxLength: o navegador cortaria o texto ANTES da máscara (colar
          // " 529.982.247-25 " perderia o último dígito). A máscara já limita a 11.
          estado={estado('cpf')}
          mensagem={mensagens.cpf}
          {...campo('cpf', formatarCpf)}
        />
      )}
      <fieldset className="flex flex-col gap-2">
        <legend className="text-sm font-semibold text-navy">{cadastro.pergunta}</legend>
        <p className="text-sm text-slate">{cadastro.perguntaAjuda}</p>
        {(['sim', 'nao', 'pular'] as const).map((v) => (
          <label key={v} className="flex min-h-toque cursor-pointer items-center gap-3 rounded-xl border border-line bg-white px-4">
            <input type="radio" value={v} className="h-5 w-5 accent-blue" {...register('tentativa')} />
            {cadastro.respostas[v]}
          </label>
        ))}
      </fieldset>
      {erro && (
        <p role="alert" className="flex items-center gap-2 text-rose-ink">
          {Icone.alerta}
          {cadastro.erros[erro] ?? erroConexao(erro)}
        </p>
      )}
      <Button type="submit" largo disabled={criar.isPending} className="mt-2">
        {cadastro.enviar}
      </Button>
      <p className="text-center text-sm text-slate">
        {cadastro.jaTenho}{' '}
        <Link to="/entrar" className="font-semibold text-blue underline">
          {cadastro.entrar}
        </Link>
      </p>
    </form>
  );
}
