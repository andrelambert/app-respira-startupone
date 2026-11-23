"""instituicao: nome curto sem Pessoa Fisica

Revision ID: fbf03767f983
Revises: ab0edd56a291
Create Date: 2026-11-23 17:41:38.539389

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
import app.models.types


# revision identifiers, used by Alembic.
revision: str = 'fbf03767f983'
down_revision: Union[str, Sequence[str], None] = 'ab0edd56a291'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """A12: encurta os nomes já gravados ("Itaú - Pessoa Física" → "Itaú").

    O catálogo só é buscado de novo a cada 7 dias; sem isto, o nome curto
    demoraria a aparecer. Usa a mesma regra do mapeamento.
    """
    from app.providers.mapping import nome_curto

    conn = op.get_bind()
    inst = sa.table("instituicao", sa.column("id", sa.Integer), sa.column("nome", sa.String))
    for id_, nome in conn.execute(sa.select(inst.c.id, inst.c.nome)).all():
        curto = nome_curto(nome)
        if curto != nome:
            conn.execute(inst.update().where(inst.c.id == id_).values(nome=curto))


def downgrade() -> None:
    """Sem volta: o nome completo é recuperado na próxima sincronização do catálogo."""
