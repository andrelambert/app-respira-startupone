import { NaoMovimenta } from '@/components/respira';
import { LinkBotao } from '@/components/ui';
import { useUsuario } from '@/hooks/queries';
import { landing } from '@/lib/copy';

/** Etapa 1 — Descoberta (§9). O gatilho é a dor, não "organizar as finanças". */
export default function Landing() {
  const { data: usuario } = useUsuario();
  return (
    <div className="flex flex-col gap-6 pt-6">
      <h1 className="text-4xl font-bold leading-tight text-navy">{landing.titulo}</h1>
      <p className="text-lg text-ink">{landing.subtitulo}</p>
      <ol className="flex flex-col gap-3">
        {landing.passos.map((p, i) => (
          <li key={p} className="flex gap-3">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-soft font-bold text-blue">
              {i + 1}
            </span>
            <span className="pt-1 text-ink">{p}</span>
          </li>
        ))}
      </ol>
      <NaoMovimenta />
      <div className="flex flex-col gap-3">
        {usuario ? (
          <LinkBotao to="/inicio" largo>
            {landing.continuar}
          </LinkBotao>
        ) : (
          <>
            <LinkBotao to="/cadastro" largo>
              {landing.cta}
            </LinkBotao>
            <LinkBotao to="/entrar" variante="secundario" largo>
              {landing.entrar}
            </LinkBotao>
          </>
        )}
        <p className="text-center text-sm text-slate">{landing.gratuito}</p>
      </div>
    </div>
  );
}
