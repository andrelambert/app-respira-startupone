"""BelvoProvider contra um transporte HTTP simulado — nenhuma chamada sai da máquina."""

import json
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from app.config import Settings
from app.models import Recurso
from app.providers.base import ErroProvedor, IdentificacaoUsuario, RecursoIndisponivel
from app.providers.belvo import PERMISSOES, BelvoProvider

USUARIO = IdentificacaoUsuario(external_id="ext-123", nome_completo="Juliana Ramos", cpf="52998224725")


def _settings() -> Settings:
    # Valores fictícios só de teste — nunca credenciais reais.
    return Settings(
        belvo_base_url="https://sandbox.belvo.test",
        belvo_secret_id="id-de-teste",
        belvo_secret_password="senha-de-teste",
        app_public_url="http://localhost:5173",
        _env_file=None,
    )


def _provider(handler) -> BelvoProvider:
    return BelvoProvider(_settings(), transport=httpx.MockTransport(handler))


async def test_token_no_clique_e_url_do_widget():
    visto = {}

    def handler(req: httpx.Request) -> httpx.Response:
        visto["path"] = req.url.path
        visto["corpo"] = json.loads(req.content)
        visto["auth"] = req.headers.get("authorization")
        return httpx.Response(200, json={"access": "tok", "refresh": "r"})

    url = await _provider(handler).criar_url_widget(USUARIO, "ofmockbank_br_retail")
    corpo = visto["corpo"]
    assert visto["path"] == "/api/token/"
    assert visto["auth"] is None  # credenciais vão no corpo, não em Basic
    assert corpo["widget"]["openfinance_feature"] == "consent_link_creation"
    consent = corpo["widget"]["consent"]
    assert consent["permissions"] == PERMISSOES == ["REGISTER", "ACCOUNTS", "CREDIT_CARDS", "CREDIT_OPERATIONS"]
    assert len(consent["purpose"]) <= 140  # limite do OpenAPI
    assert consent["identification_info"] == [{"type": "CPF", "number": "52998224725", "name": "Juliana Ramos"}]
    assert corpo["widget"]["callback_urls"]["success"] == "http://localhost:5173/conectar/sucesso"
    assert "INCOMES" not in corpo["fetch_resources"]  # add-on desligado por padrão

    q = parse_qs(urlparse(url).query)
    assert url.startswith("https://widget.belvo.io/?")
    assert q["access_token"] == ["tok"] and q["locale"] == ["pt"] and q["access_mode"] == ["recurrent"]
    assert q["country_codes"] == ["BR"] and q["external_id"] == ["ext-123"]
    assert q["institutions"] == ["ofmockbank_br_retail"]


async def test_token_sem_cpf_nao_chama_a_belvo():
    def handler(req):  # pragma: no cover - não deve ser chamado
        raise AssertionError("não deveria chamar a Belvo")

    with pytest.raises(ErroProvedor, match="cadastro_incompleto"):
        await _provider(handler).criar_url_widget(IdentificacaoUsuario("x-1", None, None))


async def test_listagem_segue_todas_as_paginas():
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.headers["authorization"].startswith("Basic ")
        pagina = int(req.url.params.get("page", "1"))
        proxima = f"https://sandbox.belvo.test/api/accounts/?link=L&page={pagina + 1}" if pagina < 3 else None
        return httpx.Response(200, json={"count": 3, "next": proxima, "previous": None, "results": [{"id": pagina}]})

    itens = await _provider(handler).listar(Recurso.ACCOUNTS, "L")
    assert [i["id"] for i in itens] == [1, 2, 3]


async def test_add_on_indisponivel_degrada():
    p = _provider(lambda req: httpx.Response(403, json=[{"code": "not_allowed"}]))
    with pytest.raises(RecursoIndisponivel):
        await p.listar(Recurso.INCOMES, "L")


async def test_revogar_usa_delete_com_barra_final():
    visto = {}

    def handler(req: httpx.Request) -> httpx.Response:
        visto["req"] = (req.method, req.url.path)
        return httpx.Response(204)

    await _provider(handler).revogar("abc")
    assert visto["req"] == ("DELETE", "/api/links/abc/")


async def test_erro_da_belvo_vira_codigo():
    p = _provider(lambda req: httpx.Response(500, json=[{"code": "institution_down"}]))
    with pytest.raises(ErroProvedor) as e:
        await p.obter_link("abc")
    assert e.value.codigo == "institution_down"


async def test_catalogo_de_instituicoes_com_os_filtros_pedidos():
    visto = []

    def handler(req: httpx.Request) -> httpx.Response:
        visto.append(dict(req.url.params))
        pagina = int(req.url.params.get("page", "1"))
        proxima = "https://sandbox.belvo.test/api/institutions/?page=2&page_size=500" if pagina == 1 else None
        return httpx.Response(200, json={"count": 2, "next": proxima, "previous": None,
                                         "results": [{"name": f"banco{pagina}", "display_name": f"Banco {pagina}"}]})

    itens = await _provider(handler).listar_instituicoes()
    assert [i["name"] for i in itens] == ["banco1", "banco2"]
    assert visto[0] | {"page": "1"} == {"country_code__in": "BR", "type": "bank", "page_size": "500", "page": "1"}
