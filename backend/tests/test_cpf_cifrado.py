"""M6 (Fase 7): CPF criptografado em repouso."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import Settings, get_settings
from app.db import engine
from app.main import _cifrar_cpfs_legados, app
from app.models import Usuario
from app.services import cripto
from tests.test_api import H


@pytest.fixture
def com_belvo(monkeypatch):
    monkeypatch.setattr(Settings, "belvo_configurada", lambda self: True)


def _cadastrar(api, email, cpf):
    return api.post(
        "/auth/registrar",
        json={"email": email, "senha": "uma-senha-forte", "nome_completo": "Pessoa Teste", "cpf": cpf},
        headers=H,
    )


def test_cpf_no_banco_nunca_e_o_numero(com_belvo):
    with TestClient(app) as api:
        r = _cadastrar(api, "cifra1@exemplo.com", "153.509.460-56")
        assert r.status_code == 201, r.text
        assert r.json()["cpf_mascarado"] == "153.***.***-56"
        with Session(engine) as s:
            u = s.exec(select(Usuario).where(Usuario.email == "cifra1@exemplo.com")).one()
        assert u.cpf and "15350946056" not in u.cpf and len(u.cpf) > 50  # token Fernet
        assert u.cpf_hash and len(u.cpf_hash) == 64 and "15350946056" not in u.cpf_hash
        assert cripto.decifrar(u.cpf) == "15350946056"


def test_cpf_em_uso_detectado_pelo_hash(com_belvo):
    with TestClient(app) as api:
        assert _cadastrar(api, "cifra2@exemplo.com", "870.484.240-52").status_code == 201
        api.cookies.clear()
        r = _cadastrar(api, "cifra3@exemplo.com", "870.484.240-52")
        assert r.status_code == 409 and r.json()["detail"] == "cpf_em_uso"


def test_sem_chave_nao_grava_cpf(com_belvo, monkeypatch):
    monkeypatch.setattr(get_settings(), "cpf_chave", None)
    with TestClient(app) as api:
        r = _cadastrar(api, "semchave@exemplo.com", "248.438.034-80")
        assert r.status_code == 503 and r.json()["detail"] == "cadastro_indisponivel"


def test_cpf_legado_em_texto_puro_e_cifrado_na_subida():
    with Session(engine) as s:
        u = Usuario(uuid_externo="legado-cpf", email="legado@exemplo.com", apelido="Legado", cpf="52998224725")
        s.add(u)
        s.commit()
        uid = u.id
    _cifrar_cpfs_legados()
    with Session(engine) as s:
        u = s.get(Usuario, uid)
        assert u is not None and u.cpf != "52998224725" and cripto.decifrar(u.cpf) == "52998224725"
        assert u.cpf_hash == cripto.hash_cpf("52998224725")


def test_chave_errada_nao_quebra_a_tela(monkeypatch):
    from cryptography.fernet import Fernet
    from pydantic import SecretStr

    token = cripto.cifrar("52998224725")
    monkeypatch.setattr(get_settings(), "cpf_chave", SecretStr(Fernet.generate_key().decode()))
    assert cripto.decifrar(token) is None
