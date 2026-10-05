"""Interface de provedor de agregação (docs/contexto-produto.md §7.11).

Dois provedores desde o dia 1: ``FixtureProvider`` (Juliana, formato Belvo) e
``BelvoProvider`` (real). Ambos devolvem JSON **no formato de resposta da
Belvo** — quem traduz para o domínio é ``mapping.py``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.models import Recurso

Json = dict[str, Any]


class ErroProvedor(Exception):
    """Falha ao falar com o provedor. ``codigo`` é estável e traduzível."""

    def __init__(self, codigo: str, detalhe: str = "") -> None:
        super().__init__(f"{codigo}: {detalhe}" if detalhe else codigo)
        self.codigo = codigo


class RecursoIndisponivel(ErroProvedor):
    """O recurso não está habilitado na conta (ex.: add-on de enriquecimento)."""


@dataclass(frozen=True)
class IdentificacaoUsuario:
    external_id: str  # sem PII (§7.3)
    nome_completo: str | None
    cpf: str | None


@dataclass(frozen=True)
class LinkInfo:
    id: str
    instituicao_codigo: str | None
    external_id: str | None
    status: str | None


@dataclass(frozen=True)
class ConsentimentoInfo:
    expira_em: datetime | None
    status: str | None


class AggregationProvider(ABC):
    nome: str

    @abstractmethod
    async def criar_url_widget(self, usuario: IdentificacaoUsuario, instituicao: str | None = None) -> str:
        """Gera o token **no momento do clique** e devolve a URL do widget.
        ``instituicao`` pré-seleciona o banco (reconexão em um toque)."""

    @abstractmethod
    async def obter_link(self, link_id: str) -> LinkInfo | None: ...

    @abstractmethod
    async def obter_consentimento(
        self, link_id: str, usuario: IdentificacaoUsuario
    ) -> ConsentimentoInfo | None: ...

    @abstractmethod
    async def listar(
        self, recurso: Recurso, link_id: str, *, desde: date | None = None, ate: date | None = None
    ) -> list[Json]:
        """Lista todas as páginas do recurso. Nunca assume uma página só."""

    @abstractmethod
    async def revogar(self, link_id: str) -> None: ...
