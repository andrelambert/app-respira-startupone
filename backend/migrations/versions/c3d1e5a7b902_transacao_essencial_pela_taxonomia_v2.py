"""transacao: essencial recalculado pela taxonomia V2

Revision ID: c3d1e5a7b902
Revises: 25f19aa131dc
Create Date: 2026-11-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d1e5a7b902'
down_revision: Union[str, Sequence[str], None] = '25f19aa131dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Transações gravadas antes da taxonomia V2 ficaram com o ``essencial``
    antigo (Alimentação inteira, inclusive bebida e loja de conveniência).
    Recalcula com a mesma regra do mapeamento, em poucos UPDATEs (sem ida e
    volta por linha — o banco publicado fica longe do servidor)."""
    from app.providers.mapping import CATEGORIAS_ESSENCIAIS, ESSENCIAIS_V2

    t = sa.table(
        "transacao",
        sa.column("direcao", sa.String),
        sa.column("categoria", sa.String),
        sa.column("subcategoria", sa.String),
        sa.column("essencial", sa.Boolean),
    )
    # O sinal vem de ``direcao``: o valor é guardado como texto (comparar em SQL não é confiável).
    saida = t.c.direcao == "SAIDA"
    op.execute(t.update().values(essencial=False))
    inteiras = [c for c, subs in ESSENCIAIS_V2.items() if subs is None]
    op.execute(t.update().where(saida, t.c.categoria.in_(inteiras)).values(essencial=True))
    for cat, subs in ESSENCIAIS_V2.items():
        if subs:
            op.execute(
                t.update().where(saida, t.c.categoria == cat, t.c.subcategoria.in_(sorted(subs))).values(essencial=True)
            )
    # Sem subcategoria (instituição que não manda), vale a categoria.
    op.execute(
        t.update()
        .where(
            saida,
            sa.or_(t.c.subcategoria.is_(None), t.c.subcategoria == ""),
            t.c.categoria.in_(sorted(CATEGORIAS_ESSENCIAIS)),
        )
        .values(essencial=True)
    )


def downgrade() -> None:
    """Sem volta: o valor antigo era o erro que esta migração corrige."""
