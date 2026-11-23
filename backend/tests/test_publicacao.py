"""M5 (Fase 7): versão pública — demo por visitante, modo público, limpeza."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from app.config import get_settings
from app.db import engine
from app.main import app
from app.models import Transacao, Usuario, agora
from app.services import auth
from app.services.demo import apagar_demos_expiradas
from tests.test_api import H


@pytest.fixture
def publico(monkeypatch):
    cfg = get_settings()
    monkeypatch.setattr(cfg, "demo_por_visitante", True)
    monkeypatch.setattr(cfg, "modo_publico", True)
    monkeypatch.setattr(cfg, "demo_por_ip_hora", 50)
    auth._eventos.clear()
    yield cfg
    auth._eventos.clear()


def _visitante():
    c = TestClient(app)
    r = c.post("/auth/demo", headers=H)
    assert r.status_code == 200, r.text
    return c, r.json()


def _aguardar(c):
    import time

    for _ in range(200):
        cs = [x for x in c.get("/consentimentos").json() if x["status"] == "ATIVO"]
        if cs and all(x["coleta_concluida"] for x in cs):
            return
        time.sleep(0.05)
    raise AssertionError("coleta não concluiu")


def test_cada_visitante_ganha_uma_juliana_so_sua(publico):
    with TestClient(app):
        a, ua = _visitante()
        b, ub = _visitante()
        _aguardar(a)
        _aguardar(b)
        assert ua["demo"] and ub["demo"] and ua["apelido"] == "Juliana"
        assert a.get("/raiox").json()["divida_total"] == b.get("/raiox").json()["divida_total"] == "20183.13"

        # O que um faz não aparece para o outro.
        assert a.post("/plano", json={"metodo": "AVALANCHE", "capacidade": "1755.00"}, headers=H).status_code == 201
        assert a.post("/demo/avancar-mes", json={"mes_dificil": False}, headers=H).status_code == 200
        assert a.get("/raiox").json()["divida_total"] != "20183.13"
        assert b.get("/raiox").json()["divida_total"] == "20183.13"
        assert b.get("/plano/ativo").status_code == 404


def test_modo_publico_sem_belvo_sem_cpf_e_noindex(publico, monkeypatch):
    monkeypatch.setattr(publico, "belvo_secret_id", "x")  # mesmo com chave, a versão pública não usa a Belvo
    with TestClient(app) as c:
        cfg = c.get("/config")
        assert cfg.json()["modo_publico"] is True and cfg.json()["belvo_configurada"] is False
        assert cfg.headers["x-robots-tag"] == "noindex, nofollow"
        r = c.post(
            "/auth/registrar",
            json={"email": "publico@exemplo.com", "senha": "uma-senha-forte", "nome_completo": "Visitante Teste"},
            headers=H,
        )
        assert r.status_code == 201, r.text
        assert r.json()["cpf_mascarado"] is None


def test_limite_por_ip_e_de_demos_ativas(publico, monkeypatch):
    with TestClient(app) as c:
        monkeypatch.setattr(publico, "demo_por_ip_hora", 2)
        auth._eventos.clear()
        assert c.post("/auth/demo", headers=H).status_code == 200
        assert c.post("/auth/demo", headers=H).status_code == 200
        r = c.post("/auth/demo", headers=H)
        assert r.status_code == 429 and r.json()["detail"] == "muitas_demos"

        auth._eventos.clear()
        monkeypatch.setattr(publico, "demo_max_ativas", 1)
        r = c.post("/auth/demo", headers=H)
        assert r.status_code == 503 and r.json()["detail"] == "demos_esgotadas"


def test_demo_vencida_e_apagada_com_todos_os_dados(publico):
    with TestClient(app):
        c, _ = _visitante()
        _aguardar(c)
        with Session(engine) as s:
            # A demo recém-criada é a de maior id com validade definida.
            u = s.exec(select(Usuario).where(col(Usuario.expira_em).is_not(None)).order_by(col(Usuario.id).desc())).first()
            assert u is not None and u.id is not None
            uid = u.id
            assert s.exec(select(Transacao).where(Transacao.usuario_id == uid)).first() is not None
            u.expira_em = agora() - timedelta(minutes=1)
            s.add(u)
            s.commit()
        assert apagar_demos_expiradas() >= 1
        with Session(engine) as s:
            assert s.get(Usuario, uid) is None
            assert s.exec(select(Transacao).where(Transacao.usuario_id == uid)).first() is None
        assert c.get("/raiox").status_code == 401  # a sessão foi junto
