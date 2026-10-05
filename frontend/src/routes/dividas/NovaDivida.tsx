import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router';
import { z } from 'zod';

import { Button, Campo, Icone } from '@/components/ui';
import { chavesFinanceiras } from '@/hooks/queries';
import { api, ApiError } from '@/lib/api';
import { erroConexao, manual as copy } from '@/lib/copy';
import { comMascara, sanitizarDinheiro, sanitizarPercentual, somenteDigitos } from '@/lib/entrada';
import { deEntradaUsuario, paraDecimal } from '@/lib/money';

const valor = z
  .string()
  .refine((v) => {
    const c = deEntradaUsuario(v);
    return c !== null && c > 0;
  }, copy.erros.valor);

const esquema = z.object({
  credor: z.string().trim().min(1, copy.erros.credor).max(60),
  modalidade: z.enum(['CREDIARIO', 'OUTRO']),
  saldo: valor,
  parcela: valor,
  taxa: z
    .string()
    .trim()
    .refine((v) => {
      if (!v) return true;
      const n = Number(v.replace(',', '.'));
      return /^\d{1,2}([.,]\d{1,4})?$/.test(v) && n >= 0.1 && n <= 20;
    }, copy.erros.taxa),
  dia: z
    .string()
    .trim()
    .refine((v) => !v || (/^\d{1,2}$/.test(v) && Number(v) >= 1 && Number(v) <= 31), copy.erros.dia),
  atraso: z.string().trim().refine((v) => !v || /^\d{1,4}$/.test(v), copy.erros.dia),
});
type Dados = z.infer<typeof esquema>;

/** Cadastro manual assistido (§7.9): obrigatórios só saldo e parcela. */
export default function NovaDivida() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<Dados>({
    resolver: zodResolver(esquema),
    defaultValues: { credor: '', modalidade: 'CREDIARIO', saldo: '', parcela: '', taxa: '', dia: '', atraso: '' },
  });
  const criar = useMutation({
    mutationFn: (d: Dados) =>
      api.criarDivida({
        credor: d.credor,
        modalidade: d.modalidade,
        saldo: paraDecimal(deEntradaUsuario(d.saldo)!),
        parcela: paraDecimal(deEntradaUsuario(d.parcela)!),
        ...(d.taxa ? { taxa_mes_percentual: d.taxa.replace(',', '.') } : {}),
        ...(d.dia ? { dia_vencimento: Number(d.dia) } : {}),
        ...(d.atraso ? { em_atraso_dias: Number(d.atraso) } : {}),
      }),
    onSuccess: async () => {
      await Promise.all(chavesFinanceiras.map((k) => qc.invalidateQueries({ queryKey: k })));
      navigate('/raiox');
    },
  });

  return (
    <form onSubmit={handleSubmit((d) => criar.mutate(d))} className="flex flex-col gap-5" noValidate>
      <div>
        <h1 className="text-2xl font-bold text-navy">{copy.titulo}</h1>
        <p className="mt-1 text-slate">{copy.subtitulo}</p>
      </div>
      <Campo rotulo={copy.credor} placeholder={copy.credorExemplo} erro={errors.credor?.message} {...register('credor')} />
      <fieldset className="flex flex-col gap-2">
        <legend className="text-sm font-semibold text-navy">{copy.tipo}</legend>
        {(['CREDIARIO', 'OUTRO'] as const).map((m) => (
          <label key={m} className="flex min-h-toque cursor-pointer items-center gap-3 rounded-xl border border-line bg-white px-4">
            <input type="radio" value={m} className="h-5 w-5 accent-blue" {...register('modalidade')} />
            {copy.tipos[m]}
          </label>
        ))}
      </fieldset>
      <Campo rotulo={copy.saldo} ajuda={copy.saldoAjuda} inputMode="decimal" placeholder="R$ 0,00" erro={errors.saldo?.message} {...comMascara(register('saldo'), sanitizarDinheiro)} />
      <Campo rotulo={copy.parcela} inputMode="decimal" placeholder="R$ 0,00" erro={errors.parcela?.message} {...comMascara(register('parcela'), sanitizarDinheiro)} />
      <Campo rotulo={copy.taxa} ajuda={copy.taxaAjuda} inputMode="decimal" placeholder="3,5" erro={errors.taxa?.message} {...comMascara(register('taxa'), sanitizarPercentual)} />
      <Campo rotulo={copy.dia} inputMode="numeric" placeholder="15" erro={errors.dia?.message} {...comMascara(register('dia'), (v) => somenteDigitos(v, 2))} />
      <Campo rotulo={copy.atraso} inputMode="numeric" placeholder="0" erro={errors.atraso?.message} {...comMascara(register('atraso'), (v) => somenteDigitos(v, 4))} />
      {criar.isError && (
        <p role="alert" className="flex items-center gap-2 text-amber-ink">
          {Icone.alerta}
          {erroConexao(criar.error instanceof ApiError ? criar.error.codigo : null)}
        </p>
      )}
      <Button type="submit" largo disabled={criar.isPending}>
        {copy.salvar}
      </Button>
    </form>
  );
}
