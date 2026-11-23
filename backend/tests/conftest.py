import os
import tempfile
from pathlib import Path

# Configuração isolada ANTES de importar a app: banco temporário, coleta sem
# atraso, sem chaves da Belvo e valores fictícios só de teste.
_tmp = Path(tempfile.mkdtemp(prefix="respira-test-"))
os.environ.update(
    {
        "DATABASE_URL": f"sqlite:///{_tmp / 'teste.db'}",
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
