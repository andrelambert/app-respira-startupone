import { EstadoVazio, LinkBotao } from '@/components/ui';
import { nav } from '@/lib/copy';

export default function NaoEncontrada() {
  return (
    <EstadoVazio
      titulo="Página não encontrada"
      texto="O endereço não existe ou mudou."
      acao={<LinkBotao to="/inicio">{nav.inicio}</LinkBotao>}
    />
  );
}
