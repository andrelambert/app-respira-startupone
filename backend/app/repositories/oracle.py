"""SQL específico do Oracle (M3, Fase 7): pacote PL/SQL do motor e versão do banco.

Exceção prevista no briefing (§4.1/§5): só isto, ``db.py``, ``models/`` e
``migrations/`` sabem que o banco é Oracle.
"""

import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlmodel import Session

PACOTE = Path(__file__).resolve().parents[2] / "oracle" / "pkg_plano_app.sql"


def _blocos(sql: str) -> list[str]:
    """Blocos PL/SQL separados por uma linha só com "/" (estilo SQL*Plus)."""
    blocos = []
    for b in re.split(r"^\s*/\s*$", sql, flags=re.MULTILINE):
        linhas = b.strip().splitlines()
        while linhas and (not linhas[0].strip() or linhas[0].strip().startswith("--")):
            linhas.pop(0)  # comentário antes do CREATE: fora, para o driver reconhecer o comando
        if linhas:
            blocos.append("\n".join(linhas).strip())
    return blocos


def instalar_pacote(engine: Engine) -> list[str]:
    """CREATE OR REPLACE do pkg_plano_app. Devolve os erros de compilação (vazio = ok)."""
    with engine.begin() as c:
        for bloco in _blocos(PACOTE.read_text(encoding="utf-8")):
            c.exec_driver_sql(bloco)
        erros = c.execute(
            text(
                "SELECT name || ' linha ' || line || ': ' || text FROM user_errors "
                "WHERE name = 'PKG_PLANO_APP' ORDER BY sequence"
            )
        ).scalars()
        return [str(e).strip() for e in erros]


def simular(session: Session, usuario_id: int, metodo: str, capacidade: Decimal) -> dict[str, Any]:
    """Roda o motor em PL/SQL. ``juros`` volta como Decimal exato."""
    bruto = session.exec(  # type: ignore[call-overload]
        text("SELECT pkg_plano_app.simular(:u, :m, :c) FROM dual"),
        params={"u": usuario_id, "m": metodo, "c": capacidade},
    ).scalar_one()
    return json.loads(bruto, parse_float=Decimal, parse_int=int)


def versao(session: Session) -> str | None:
    """Versão completa do banco, se o usuário da aplicação puder ler."""
    for sql in (
        "SELECT version_full FROM product_component_version WHERE ROWNUM = 1",
        "SELECT banner_full FROM v$version WHERE ROWNUM = 1",
    ):
        try:
            v = session.exec(text(sql)).scalar_one_or_none()  # type: ignore[call-overload]
            if v:
                return str(v).strip()
        except Exception:  # noqa: BLE001 — sem privilégio de leitura: tenta a próxima
            session.rollback()
    return None
