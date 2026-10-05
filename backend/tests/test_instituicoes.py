"""Catálogo da Belvo como fonte da verdade de nome/logo dos bancos."""

from decimal import Decimal as D

from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Divida, Instituicao, Origem, TipoInstituicao, Usuario
from app.providers.mapping import InstituicaoCatalogo
from app.repositories import consentimentos as repo_c


def _sessao() -> Session:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_banco_conectado_antes_do_catalogo_ganha_nome_logo_e_descricoes():
    s = _sessao()
    u = Usuario(uuid_externo="u-1", apelido="Teste")
    s.add(u)
    s.commit()
    # Conexão chegou antes do catálogo: nome = código da Belvo
    inst = repo_c.instituicao(s, "ofnubank_br_retail", "ofnubank_br_retail", TipoInstituicao.BANCO)
    s.add(
        Divida(
            usuario_id=u.id, instituicao_id=inst.id, modalidade="CARTAO_FATURA",
            descricao="Fatura do cartão ofnubank_br_retail", saldo_devedor=D("100"), saldo_inicial=D("100"),
            taxa_juros_mes=D("0"), parcela_minima=D("100"), origem=Origem.OPEN_FINANCE,
        )
    )
    s.commit()

    total = repo_c.aplicar_catalogo(
        s,
        [InstituicaoCatalogo("ofnubank_br_retail", "Nubank", "https://x/text.svg", "https://x/icon.svg"),
         InstituicaoCatalogo("ofitau_br_retail", "Itaú", None, "https://x/itau.svg")],
    )
    assert total == 2
    nubank = repo_c.instituicao_por_codigo(s, "ofnubank_br_retail")
    assert (nubank.nome, nubank.logo_url, nubank.icone_url) == ("Nubank", "https://x/text.svg", "https://x/icon.svg")
    assert nubank.catalogo_em is not None
    assert s.exec(select(Divida)).one().descricao == "Fatura do cartão Nubank"
    assert repo_c.instituicao_por_codigo(s, "ofitau_br_retail").nome == "Itaú"

    # Uma nova conexão não sobrescreve o nome do catálogo com o código
    repo_c.instituicao(s, "ofnubank_br_retail", "ofnubank_br_retail", TipoInstituicao.BANCO)
    assert repo_c.instituicao_por_codigo(s, "ofnubank_br_retail").nome == "Nubank"
    assert len(s.exec(select(Instituicao)).all()) == 2
