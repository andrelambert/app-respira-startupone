"""Provedor de cada usuário e relógio do usuário.

O provedor é POR USUÁRIO: a conta de demonstração (Juliana) usa o
``FixtureProvider``; toda conta registrada usa a Belvo real.
"""

from datetime import date

from app.config import get_settings
from app.domain.planner import adicionar_meses
from app.models import Usuario
from app.providers.base import AggregationProvider, ErroProvedor
from app.providers.fixture import FixtureProvider

_fixture: FixtureProvider | None = None
_belvo: AggregationProvider | None = None


def fixture() -> FixtureProvider:
    global _fixture
    if _fixture is None:
        _fixture = FixtureProvider(get_settings().app_public_url)
    return _fixture


def belvo() -> AggregationProvider:
    global _belvo
    if _belvo is None:
        s = get_settings()
        if not s.belvo_configurada():
            raise ErroProvedor("belvo_nao_configurada", "defina BELVO_SECRET_ID/PASSWORD no backend/.env")
        from app.providers.belvo import BelvoProvider

        _belvo = BelvoProvider(s, enriquecimento=s.belvo_enrichment_enabled)
    return _belvo


def provider(usuario: Usuario) -> AggregationProvider:
    return fixture() if usuario.demo else belvo()


def hoje_do_usuario(usuario: Usuario | None) -> date:
    """Data de hoje — deslocada pelo relógio de demonstração, só na conta demo."""
    hoje = date.today()
    if usuario is None or not usuario.demo or not usuario.meses_simulados:
        return hoje
    alvo = adicionar_meses(hoje.replace(day=1), usuario.meses_simulados)
    ultimo = (adicionar_meses(alvo, 1) - alvo).days
    return alvo.replace(day=min(hoje.day, ultimo))
