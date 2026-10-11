import { useState } from 'react';
import { useSearchParams } from 'react-router';

import { NaoMovimenta } from '@/components/respira';
import { Button, Card } from '@/components/ui';
import { api, ApiError } from '@/lib/api';

/**
 * Widget SIMULADO — só a conta demo (FixtureProvider) chega aqui. Imita o caminho do
 * widget real (escolher banco → autorizar no banco → callback) para a
 * demonstração rodar sem credenciais e sem dado bancário real.
 */
const BANCOS = [
  { codigo: 'ofnubank_br_retail', nome: 'Nubank', nota: 'conta, cartão no rotativo e empréstimo pessoal' },
  { codigo: 'ofitau_br_retail', nome: 'Itaú', nota: 'conta no cheque especial, cartão parcelado e moto financiada' },
  { codigo: 'ofcaixa_br_retail', nome: 'Caixa', nota: 'poupança, consignado e crédito pessoal em atraso' },
  { codigo: 'fixture_banco_fora_br_retail', nome: 'Banco Fora do Ar', nota: 'simula banco fora do ar' },
];

export default function WidgetSimulado() {
  const [params] = useSearchParams();
  const token = params.get('access_token') ?? '';
  const preSelecionado = params.get('institutions');
  const [banco, setBanco] = useState(BANCOS.find((b) => b.codigo === preSelecionado) ?? null);
  const [enviando, setEnviando] = useState(false);

  async function autorizar() {
    if (!banco) return;
    setEnviando(true);
    try {
      const { link, institution } = await api.autorizarFixture(token, banco.codigo);
      window.location.replace(`/conectar/sucesso?link=${link}&institution=${institution}`);
    } catch (e) {
      const codigo = e instanceof ApiError ? e.codigo : 'unexpected_error';
      window.location.replace(
        `/conectar/saida?last_encountered_error_code=${encodeURIComponent(codigo)}&meta_data_institution_name=${encodeURIComponent(banco.nome)}`,
      );
    }
  }

  return (
    <div className="flex flex-col gap-4 pt-2">
      <p className="rounded-xl bg-amber-soft px-3 py-2 text-sm font-semibold text-amber-ink">
        Demonstração — nenhum banco real é acessado.
      </p>
      {!banco ? (
        <>
          <h1 className="text-2xl font-bold text-navy">Escolha seu banco</h1>
          <ul className="flex flex-col gap-2">
            {BANCOS.map((b) => (
              <li key={b.codigo}>
                <button
                  type="button"
                  onClick={() => setBanco(b)}
                  className="flex min-h-toque w-full flex-col items-start rounded-xl border border-line bg-white px-4 py-3 text-left hover:border-blue"
                >
                  <span className="font-semibold text-navy">{b.nome}</span>
                  <span className="text-sm text-slate">{b.nota}</span>
                </button>
              </li>
            ))}
          </ul>
          <Button variante="fantasma" onClick={() => window.location.replace('/conectar/saida?meta_data_step=abandon-survey')}>
            Sair
          </Button>
        </>
      ) : (
        <Card className="flex flex-col gap-4">
          <h1 className="text-2xl font-bold text-navy">Você está no app do {banco.nome}</h1>
          <p>
            O Respira pede para <strong>ler</strong> seus dados cadastrais, contas, cartões e operações de crédito.
            A autorização vale por 12 meses e pode ser cancelada a qualquer momento.
          </p>
          <NaoMovimenta />
          <Button largo onClick={autorizar} disabled={enviando}>
            Autorizar compartilhamento
          </Button>
          <Button
            largo
            variante="secundario"
            onClick={() => window.location.replace('/conectar/saida?meta_data_step=abandon-survey')}
          >
            Cancelar
          </Button>
        </Card>
      )}
    </div>
  );
}
