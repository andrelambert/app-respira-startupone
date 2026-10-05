"""Cliente HTTP da Belvo — OFDA Brasil (docs/contexto-produto.md §7).

Toda chamada à Belvo sai daqui; nenhuma sai do navegador (§12.1).

Regras de log (§12.4): nunca imprimir corpo de requisição (o token leva secret
e CPF), nem URL com ``user_document``. O logger do httpx fica em WARNING em
``main.py`` para não registrar URLs.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import Settings
from app.models import Recurso
from app.providers.base import (
    AggregationProvider,
    ConsentimentoInfo,
    ErroProvedor,
    IdentificacaoUsuario,
    Json,
    LinkInfo,
    RecursoIndisponivel,
)

log = logging.getLogger("respira.belvo")

ESCOPOS = (
    "read_institutions,write_links,read_consents,write_consents,"
    "write_consent_callback,delete_consents"
)
# Exatamente as quatro que o MVP usa — minimização (§7.2, §12.7).
PERMISSOES = ["REGISTER", "ACCOUNTS", "CREDIT_CARDS", "CREDIT_OPERATIONS"]
RECURSOS_BASE = ["ACCOUNTS", "OWNERS", "TRANSACTIONS", "BILLS"]
RECURSOS_ENRIQUECIMENTO = ["INCOMES", "RECURRING_EXPENSES"]
# Aparece para o usuário na tela do banco. Linguagem de gente (§11), máx. 140.
PROPOSITO = (
    "Organizar suas dívidas e calcular um plano para você sair delas, "
    "com acompanhamento mês a mês."
)

CAMINHOS: dict[Recurso, str] = {
    Recurso.OWNERS: "/api/owners/",
    Recurso.ACCOUNTS: "/api/accounts/",
    Recurso.TRANSACTIONS: "/api/transactions/",
    Recurso.BILLS: "/api/bills/",
    Recurso.INCOMES: "/api/incomes/",
    Recurso.RECURRING_EXPENSES: "/api/recurring-expenses/",
}
PAGE_SIZE = 1000
MAX_PAGINAS = 200  # trava de segurança contra paginação infinita


class BelvoProvider(AggregationProvider):
    nome = "belvo"

    def __init__(
        self,
        settings: Settings,
        enriquecimento: bool = False,
        transport: httpx.AsyncBaseTransport | None = None,  # só para testes
    ) -> None:
        if not settings.belvo_configurada():
            raise ErroProvedor("belvo_nao_configurada", "defina BELVO_SECRET_ID/PASSWORD no .env")
        self._s = settings
        self._enriquecimento = enriquecimento
        self._transport = transport
        assert settings.belvo_secret_id and settings.belvo_secret_password
        self._auth = (
            settings.belvo_secret_id.get_secret_value(),
            settings.belvo_secret_password.get_secret_value(),
        )

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._s.belvo_base_url,
            auth=self._auth,
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={"Accept": "application/json"},
            transport=self._transport,
        )

    # --- token + widget (§7.2, §7.3) ----------------------------------------

    async def criar_url_widget(self, usuario: IdentificacaoUsuario, instituicao: str | None = None) -> str:
        if not (usuario.cpf and usuario.nome_completo):
            raise ErroProvedor("cadastro_incompleto", "nome completo e CPF são necessários")
        base = self._s.app_public_url.rstrip("/")
        corpo = {
            "id": self._auth[0],
            "password": self._auth[1],
            "scopes": ESCOPOS,
            "stale_in": self._s.belvo_stale_in,
            "fetch_resources": RECURSOS_BASE + (RECURSOS_ENRIQUECIMENTO if self._enriquecimento else []),
            "widget": {
                "openfinance_feature": "consent_link_creation",
                "callback_urls": {
                    "success": f"{base}/conectar/sucesso",
                    "exit": f"{base}/conectar/saida",
                    "event": f"{base}/conectar/evento",
                },
                "consent": {
                    # Conferido no OpenAPI: o propósito vai em widget.consent.purpose
                    # (o exemplo do guia o coloca em widget.purpose).
                    "purpose": PROPOSITO,
                    "terms_and_conditions_url": self._s.app_terms_url,
                    "permissions": PERMISSOES,
                    "identification_info": [
                        {"type": "CPF", "number": usuario.cpf, "name": usuario.nome_completo}
                    ],
                },
                "branding": {
                    "company_name": "Respira",
                    "company_logo": f"{base}/logo.svg",
                    "company_icon": f"{base}/icon.svg",
                    "company_terms_url": self._s.app_terms_url,
                    "overlay_background_color": "#F8FAFC",
                    "social_proof": True,
                },
            },
        }
        async with self._client() as c:
            # Credenciais vão no corpo (é o contrato do /api/token/). Nunca logar.
            r = await c.post("/api/token/", json=corpo, auth=None)
        if r.status_code >= 400:
            log.error("belvo_token_falhou status=%s", r.status_code)
            raise ErroProvedor("token_falhou", f"status {r.status_code}")
        access = r.json().get("access")
        if not access:
            raise ErroProvedor("token_sem_access")
        params = {
            "access_token": access,
            "locale": "pt",
            "access_mode": "recurrent",
            "country_codes": "BR",
            "institution_types": "retail",
            "external_id": usuario.external_id,
        }
        if instituicao:
            params["institutions"] = instituicao
        return f"{self._s.belvo_widget_url.rstrip('/')}/?{urlencode(params)}"

    # --- links e consentimentos (§7.10) ---------------------------------------

    async def obter_link(self, link_id: str) -> LinkInfo | None:
        async with self._client() as c:
            r = await c.get(f"/api/links/{link_id}/")
        if r.status_code == 404:
            return None
        self._checar(r, "link")
        d = r.json()
        return LinkInfo(
            id=d.get("id", link_id),
            instituicao_codigo=d.get("institution"),
            external_id=d.get("external_id"),
            status=d.get("status"),
        )

    async def obter_consentimento(
        self, link_id: str, usuario: IdentificacaoUsuario
    ) -> ConsentimentoInfo | None:
        if not usuario.cpf:
            return None
        async with self._client() as c:
            # user_document leva CPF na query: por isso o httpx não loga URL.
            itens = await self._paginar(c, "/api/consents/", {"user_document": usuario.cpf})
        for item in itens:
            if item.get("link_id") == link_id:
                exp = item.get("expired_at")
                return ConsentimentoInfo(
                    expira_em=datetime.fromisoformat(exp.replace("Z", "+00:00")) if exp else None,
                    status=item.get("status"),
                )
        return None

    async def revogar(self, link_id: str) -> None:
        async with self._client() as c:
            r = await c.delete(f"/api/links/{link_id}/")
        if r.status_code in (204, 404):
            return  # 404: já não existe na Belvo — local será apagado do mesmo jeito
        self._checar(r, "revogar")

    # --- catálogo de instituições ----------------------------------------------

    async def listar_instituicoes(self) -> list[Json]:
        """Bancos do Brasil. Dado público e quase estático: vira o catálogo local."""
        async with self._client() as c:
            return await self._paginar(
                c, "/api/institutions/", {"country_code__in": "BR", "type": "bank", "page_size": 500}
            )

    # --- leitura paginada (§7.6) ----------------------------------------------

    async def listar(
        self, recurso: Recurso, link_id: str, *, desde: date | None = None, ate: date | None = None
    ) -> list[Json]:
        params: dict[str, Any] = {"link": link_id}
        if recurso is Recurso.TRANSACTIONS and desde and ate:
            params["value_date__range"] = f"{desde.isoformat()},{ate.isoformat()}"
        async with self._client() as c:
            return await self._paginar(c, CAMINHOS[recurso], params, recurso=recurso)

    async def _paginar(
        self,
        c: httpx.AsyncClient,
        caminho: str,
        params: dict[str, Any],
        recurso: Recurso | None = None,
    ) -> list[Json]:
        resultados: list[Json] = []
        url: str | None = caminho
        query: dict[str, Any] | None = {"page": 1, "page_size": PAGE_SIZE, **params}
        for _ in range(MAX_PAGINAS):
            if url is None:
                break
            r = await c.get(url, params=query)
            if recurso in (Recurso.INCOMES, Recurso.RECURRING_EXPENSES) and r.status_code in (
                400, 401, 403, 404,
            ):
                raise RecursoIndisponivel("enriquecimento_indisponivel", recurso.value)
            self._checar(r, caminho)
            d = r.json()
            if isinstance(d, list):  # alguns endpoints devolvem lista crua
                resultados.extend(d)
                break
            resultados.extend(d.get("results") or [])
            # ``next`` já carrega os parâmetros da consulta.
            url, query = d.get("next"), None
        return resultados

    @staticmethod
    def _checar(r: httpx.Response, contexto: str) -> None:
        if r.status_code < 400:
            return
        codigo = "erro_belvo"
        try:
            corpo = r.json()
            if isinstance(corpo, list) and corpo:
                codigo = corpo[0].get("code") or codigo
            elif isinstance(corpo, dict):
                codigo = corpo.get("code") or codigo
        except ValueError:
            pass
        log.warning("belvo_erro contexto=%s status=%s codigo=%s", contexto, r.status_code, codigo)
        raise ErroProvedor(codigo, f"{contexto} status {r.status_code}")
