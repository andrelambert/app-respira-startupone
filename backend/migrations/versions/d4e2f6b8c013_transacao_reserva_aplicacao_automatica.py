"""transacao: reserva (aplicação automática) e estorno fora da renda

Revision ID: d4e2f6b8c013
Revises: c3d1e5a7b902
Create Date: 2026-11-25 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e2f6b8c013'
down_revision: Union[str, Sequence[str], None] = 'c3d1e5a7b902'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Coluna ``reserva`` e reclassificação do que já está gravado.

    A contraparte não fica gravada; por isso aqui valem o tipo de operação, a
    descrição e a categoria de investimento — só em conta de depósito. A próxima
    coleta aplica a regra completa do mapeamento. Poucos UPDATEs, sem ida e volta
    por linha (o banco publicado fica longe do servidor). O sinal vem de ``direcao``:
    o valor é guardado como texto, e comparar o sinal em SQL não é confiável."""
    from app.providers.mapping import (
        CATEGORIA_INVESTIMENTO,
        OPERACAO_RESGATE,
        PREFIXOS_APLICACAO,
        PREFIXOS_ESTORNO,
        PREFIXOS_RESGATE,
    )

    with op.batch_alter_table('transacao', schema=None) as batch_op:
        batch_op.add_column(sa.Column('reserva', sa.Boolean(), nullable=False, server_default=sa.false()))

    t = sa.table(
        "transacao",
        sa.column("conta_id", sa.Integer),
        sa.column("direcao", sa.String),
        sa.column("descricao", sa.String),
        sa.column("tipo_operacao", sa.String),
        sa.column("categoria", sa.String),
        sa.column("essencial", sa.Boolean),
        sa.column("entrada_renda", sa.Boolean),
        sa.column("reserva", sa.Boolean),
    )
    conta = sa.table("conta", sa.column("id", sa.Integer), sa.column("tipo", sa.String))
    deposito = t.c.conta_id.in_(sa.select(conta.c.id).where(conta.c.tipo.in_(["CORRENTE", "POUPANCA", "PAGAMENTO"])))
    desc = sa.func.upper(sa.func.coalesce(t.c.descricao, ""))

    def comeca(prefixos):
        return sa.or_(*[desc.like(f"{p}%") for p in prefixos])

    e_reserva = sa.or_(
        t.c.tipo_operacao == OPERACAO_RESGATE,
        sa.and_(t.c.direcao == "ENTRADA", comeca(PREFIXOS_RESGATE)),
        sa.and_(t.c.direcao == "SAIDA", comeca(PREFIXOS_APLICACAO)),
        t.c.categoria == CATEGORIA_INVESTIMENTO,
    )
    op.execute(t.update().where(deposito, e_reserva).values(reserva=True, entrada_renda=False, essencial=False))
    op.execute(t.update().where(t.c.direcao == "ENTRADA", comeca(PREFIXOS_ESTORNO)).values(entrada_renda=False))


def downgrade() -> None:
    with op.batch_alter_table('transacao', schema=None) as batch_op:
        batch_op.drop_column('reserva')
