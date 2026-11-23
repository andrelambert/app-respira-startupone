"""M2 (Fase 7): o esquema compila para o Oracle — sem precisar de banco.

Compila o ``CREATE TABLE`` de todas as tabelas dos modelos com o dialeto Oracle
e confere as armadilhas conhecidas (docs: FASE7-CONTEXTO-AGENTE §4.3). Roda em
qualquer máquina e impede regressão quando alguém mexe num modelo.
"""

import re

import pytest
from sqlalchemy import Integer
from sqlalchemy.dialects import oracle
from sqlalchemy.schema import CreateIndex, CreateTable
from sqlmodel import SQLModel

import app.models  # noqa: F401 — registra as tabelas

DIALETO = oracle.dialect()
TABELAS = sorted(SQLModel.metadata.tables.values(), key=lambda t: t.name)


def _ddl(tabela) -> str:
    return str(CreateTable(tabela).compile(dialect=DIALETO))


@pytest.mark.parametrize("tabela", TABELAS, ids=lambda t: t.name)
def test_create_table_compila_no_oracle(tabela):
    ddl = _ddl(tabela)
    # VARCHAR2 sem tamanho é DDL inválido no Oracle.
    assert not re.search(r"VARCHAR2(?!\s*\()", ddl), ddl


@pytest.mark.parametrize("tabela", TABELAS, ids=lambda t: t.name)
def test_pk_inteira_e_gerada_pelo_banco(tabela):
    """Sem IDENTITY o Oracle não gera o id e o insert falha (ORA-01400)."""
    pks = list(tabela.primary_key.columns)
    if len(pks) == 1 and isinstance(pks[0].type, Integer):
        assert "GENERATED" in _ddl(tabela) and "IDENTITY" in _ddl(tabela), tabela.name


def test_indices_compilam_no_oracle():
    for t in TABELAS:
        for i in t.indexes:
            str(CreateIndex(i).compile(dialect=DIALETO))


def test_nomes_cabem_no_oracle():
    """Identificadores de até 128 bytes (Oracle 12.2+); nada de palavra reservada crua."""
    for t in TABELAS:
        assert len(t.name) <= 128
        for c in t.columns:
            assert len(c.name) <= 128, (t.name, c.name)


def test_dinheiro_e_taxa_sao_number_sem_escala_no_oracle():
    """NUMERIC sem precisão é NUMBER(38) no Oracle — inteiro: R$ 20.183,13 viraria
    R$ 20.183 e a taxa de 0,1502 viraria 0. Tem de ser NUMBER puro."""
    from app.models.types import DecimalTexto

    colunas = [
        (t.name, c.name) for t in TABELAS for c in t.columns if isinstance(c.type, DecimalTexto)
    ]
    assert ("divida", "taxa_juros_mes") in colunas and ("divida", "saldo_devedor") in colunas
    for tabela, coluna in colunas:
        linha = next(
            ln for ln in _ddl(SQLModel.metadata.tables[tabela]).splitlines() if ln.strip().startswith(coluna + " ")
        )
        assert re.match(rf"\s*{coluna} NUMBER\b(?!\s*\()", linha), linha


@pytest.mark.oracle
def test_decimal_volta_exato_do_oracle():
    """Ida e volta no banco de verdade: centavos e taxa com 6 casas, sem arredondar."""
    from decimal import Decimal

    from sqlalchemy import Column, MetaData, Table, select

    from app.db import engine
    from app.models.types import DecimalTexto

    md = MetaData()
    t = Table("teste_decimal_m2", md, Column("v", DecimalTexto))
    md.drop_all(engine)
    md.create_all(engine)
    try:
        valores = [Decimal("20183.13"), Decimal("0.150200"), Decimal("-0.01"), Decimal("123456789012.34")]
        with engine.begin() as c:
            c.execute(t.insert(), [{"v": v} for v in valores])
            lidos = [r[0] for r in c.execute(select(t.c.v))]
        assert sorted(lidos) == sorted(valores)
    finally:
        md.drop_all(engine)
