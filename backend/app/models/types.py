"""Tipos de coluna que se comportam igual no SQLite e no Oracle (M2, Fase 7).

Só esta pasta (e ``db.py``/``migrations``) sabe qual banco está em uso.
"""

import json
from decimal import Decimal
from typing import Any

from sqlalchemy import Numeric, String, Text
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeDecorator, TypeEngine


class DecimalTexto(TypeDecorator[Decimal]):
    """Dinheiro e taxas como ``Decimal`` exato nos dois bancos.

    - SQLite: texto. O SQLite não tem decimal nativo e guardaria ``Numeric`` como
      REAL (float) — bug de correção para dinheiro (§12.13). Como texto, o valor
      volta exatamente igual.
    - Oracle: ``NUMBER`` sem precisão nem escala (exato até 38 dígitos). Permite
      somar e ordenar em SQL e a conferência do motor em PL/SQL (§5 do briefing).
    """

    impl = String(40)
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        if dialect.name == "oracle":
            return dialect.type_descriptor(Numeric(asdecimal=True))
        return dialect.type_descriptor(String(40))

    def process_bind_param(self, value: Decimal | None, dialect: Dialect) -> Any:
        if value is None:
            return None
        d = Decimal(value)
        return d if dialect.name == "oracle" else str(d)

    def process_result_value(self, value: Any, dialect: Dialect) -> Decimal | None:
        # str() antes: se o driver devolver float, não herda o erro binário.
        return None if value is None else Decimal(str(value))


class JsonTexto(TypeDecorator[Any]):
    """JSON guardado como texto (``CLOB`` no Oracle).

    O ``sa.JSON`` não compila no dialeto Oracle. No SQLite o JSON já era texto,
    então os dados existentes continuam legíveis.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> str | None:
        return None if value is None else json.dumps(value, ensure_ascii=False)

    def process_result_value(self, value: Any, dialect: Dialect) -> Any:
        if value is None:
            return None
        if not isinstance(value, str):  # LOB do driver
            value = value.read() if hasattr(value, "read") else str(value)
        return json.loads(value)


class TextoOpcional(TypeDecorator[str]):
    """Texto que pode ser vazio.

    O Oracle trata ``''`` como ``NULL``: gravar string vazia numa coluna
    ``NOT NULL`` falha. A coluna é anulável e a leitura devolve ``""`` no lugar de
    ``None``, então o resto do código continua vendo ``str``.
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        return value or None

    def process_result_value(self, value: str | None, dialect: Dialect) -> str:
        return value or ""
