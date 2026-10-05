from decimal import Decimal

from sqlalchemy import String
from sqlalchemy.types import TypeDecorator


class DecimalTexto(TypeDecorator[Decimal]):
    """Decimal persistido como texto.

    O SQLite não tem tipo decimal nativo e guardaria ``Numeric`` como REAL
    (float) — bug de correção para dinheiro (§12.13). Como texto, o valor
    volta exatamente igual. No Oracle isto vira ``NUMBER(p, s)``.
    """

    impl = String(40)
    cache_ok = True

    def process_bind_param(self, value: Decimal | None, dialect) -> str | None:
        if value is None:
            return None
        return str(Decimal(value))

    def process_result_value(self, value: str | None, dialect) -> Decimal | None:
        return None if value is None else Decimal(value)
