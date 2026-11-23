import os
import tempfile
from pathlib import Path

# Configuração isolada ANTES de importar a app: banco temporário, coleta sem
# atraso, sem chaves da Belvo e valores fictícios só de teste.
#
# Suíte no Oracle (M2): defina TEST_DATABASE_URL=oracle+oracledb://@ e as ORACLE_*
# do schema de TESTE no ambiente. Nunca o schema da aplicação: o usuário precisa
# terminar em _TESTE, e as ORACLE_* precisam vir do ambiente (não do .env, que
# aponta para o RESPIRA_APP).
_tmp = Path(tempfile.mkdtemp(prefix="respira-test-"))
_url_teste = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_tmp / 'teste.db'}"
if _url_teste.startswith("oracle"):
    _usuario = os.environ.get("ORACLE_USER", "")
    if not _usuario.upper().endswith("_TESTE"):
        raise SystemExit(
            "TEST_DATABASE_URL aponta para o Oracle, mas ORACLE_USER não é um schema de teste "
            f"(recebi {_usuario or 'vazio'!r}). A suíte só roda no RESPIRA_TESTE."
        )
os.environ.update(
    {
        "DATABASE_URL": _url_teste,
        "FIXTURE_COLETA_SEGUNDOS": "0",
        "BELVO_WEBHOOK_TOKEN": "token-de-teste",
        "BELVO_SECRET_ID": "",
        "BELVO_SECRET_PASSWORD": "",
        "DEMO_EMAIL": "demo@teste.local",
        "DEMO_SENHA": "senha-demo-de-teste",
        "LOG_LEVEL": "WARNING",
    }
)


import pytest


def pytest_collection_modifyitems(config, items):
    """Testes marcados com @pytest.mark.oracle só rodam no Oracle."""
    if _url_teste.startswith("oracle"):
        return
    pular = pytest.mark.skip(reason="só no Oracle (TEST_DATABASE_URL)")
    for item in items:
        if "oracle" in item.keywords:
            item.add_marker(pular)


@pytest.fixture(scope="session", autouse=True)
def _oracle_schema_de_teste_limpo():
    """No Oracle o schema de teste persiste entre execuções: começa vazio, para
    a subida do app passar pelo bootstrap (create_all + stamp), como num banco novo.
    Só roda com o usuário *_TESTE (checado acima)."""
    if _url_teste.startswith("oracle"):
        from sqlalchemy import text
        from sqlmodel import SQLModel

        import app.models  # noqa: F401
        from app.db import engine

        SQLModel.metadata.drop_all(engine)
        with engine.begin() as c:
            c.execute(text("BEGIN EXECUTE IMMEDIATE 'DROP TABLE alembic_version'; EXCEPTION WHEN OTHERS THEN NULL; END;"))
    yield


@pytest.fixture
def demo_limpa(api):
    """Entra na Juliana do zero e devolve a demo ao começo para os outros módulos.

    Usa o ``api`` (TestClient) do módulo que pede a fixture.
    """
    from tests.test_api import DEMO, H, _aguardar_coleta

    api.cookies.clear()
    assert api.post("/auth/entrar", json=DEMO, headers=H).status_code == 200
    assert api.post("/demo/reiniciar", headers=H).status_code == 204
    _aguardar_coleta(api)
    yield api
    assert api.post("/demo/reiniciar", headers=H).status_code == 204
    _aguardar_coleta(api)
