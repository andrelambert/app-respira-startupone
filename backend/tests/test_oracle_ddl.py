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
