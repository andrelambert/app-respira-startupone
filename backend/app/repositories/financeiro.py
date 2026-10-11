"""Contas, dívidas, transações e renda detectada. Reconciliação sempre por
*upsert* no ``id_externo`` da Belvo — webhook duplicado não duplica dado."""

from datetime import date
from decimal import Decimal

from sqlmodel import Session, col, select

from app.models import (
    Consentimento,
    Conta,
    Direcao,
    Divida,
    Fatura,
    Origem,
    RendaDetectada,
    StatusConsentimento,
    TaxaOrigem,
    Transacao,
    agora,
)
from app.providers.mapping import ContaMapeada, DividaMapeada, FaturaMapeada, TransacaoMapeada


def upsert_conta(
    session: Session, usuario_id: int, consentimento_id: int, instituicao_id: int, m: ContaMapeada
) -> Conta:
    conta = session.exec(select(Conta).where(Conta.id_externo == m.id_externo)).first()
    if conta is None:
        conta = Conta(
            usuario_id=usuario_id,
            consentimento_id=consentimento_id,
            instituicao_id=instituicao_id,
            id_externo=m.id_externo,
            tipo=m.tipo,
        )
    conta.tipo = m.tipo
    conta.nome = m.nome
    conta.numero_final = m.numero_final
    conta.tipo_externo = m.tipo_externo
    conta.agencia = m.agencia
    conta.numero_conta = m.numero_conta
    conta.saldo = m.saldo
    conta.disponivel = m.disponivel
    conta.limite_credito = m.limite_credito
    conta.limite_cheque_especial = m.limite_cheque_especial
    conta.usado_cheque_especial = m.usado_cheque_especial
    conta.atualizado_em = agora()
    session.add(conta)
    session.flush()
    # Transações que chegaram antes da conta (webhooks sem ordem garantida)
    # ficam só com o account.id da Belvo; amarra-as agora.
    for t in session.exec(
        select(Transacao).where(Transacao.conta_id_externo == m.id_externo, col(Transacao.conta_id).is_(None))
    ):
        t.conta_id = conta.id
        session.add(t)
    return conta


def upsert_fatura(
    session: Session, usuario_id: int, consentimento_id: int, conta_id: int, m: FaturaMapeada
) -> Fatura:
    f = session.exec(select(Fatura).where(Fatura.id_externo == m.id_externo)).first() or Fatura(
        usuario_id=usuario_id, consentimento_id=consentimento_id, conta_id=conta_id, id_externo=m.id_externo
    )
    f.conta_id = conta_id
    f.nome = m.nome
    f.vencimento = m.vencimento
    f.total = m.total
    f.minimo = m.minimo
    f.pago = m.pago
    f.encargos = m.encargos
    f.parcelada = m.parcelada
    f.pagamentos = [
        {"data": p.data.isoformat() if p.data else None, "valor": str(p.valor)} for p in m.pagamentos
    ]
    f.atualizado_em = agora()
    session.add(f)
    return f


def upsert_divida(
    session: Session,
    usuario_id: int,
    consentimento_id: int,
    instituicao_id: int,
    m: DividaMapeada,
) -> Divida:
    d = session.exec(select(Divida).where(Divida.id_externo == m.id_externo)).first()
    if d is None:
        d = Divida(
            usuario_id=usuario_id,
            consentimento_id=consentimento_id,
            instituicao_id=instituicao_id,
            id_externo=m.id_externo,
            modalidade=m.modalidade,
            descricao=m.descricao,
            saldo_devedor=m.saldo_devedor,
            saldo_inicial=m.saldo_devedor,
            taxa_juros_mes=m.taxa_juros_mes,
            parcela_minima=m.parcela_minima,
            origem=Origem.OPEN_FINANCE,
        )
    # O usuário confirmou taxa/parcela que o banco não entrega: a sincronização
    # não sobrescreve o que ele informou com uma estimativa.
    usuario_confirmou_taxa = d.id is not None and d.taxa_origem == TaxaOrigem.INFORMADA
    if m.taxa_origem == "INFORMADA" or not usuario_confirmou_taxa:
        d.taxa_juros_mes = m.taxa_juros_mes
        d.taxa_origem = TaxaOrigem(m.taxa_origem)
    if not m.parcela_estimada or d.id is None or d.parcela_estimada:
        d.parcela_minima = m.parcela_minima
        d.parcela_estimada = m.parcela_estimada
    d.modalidade = m.modalidade
    d.descricao = m.descricao
    d.saldo_devedor = m.saldo_devedor
    d.parcelas_restantes = m.parcelas_restantes
    d.dia_vencimento = m.dia_vencimento
    d.em_atraso_dias = m.em_atraso_dias
    d.conta_id_externo = m.conta_id_externo
    d.valor_contratado = m.valor_contratado
    d.parcelas_total = m.parcelas_total
    d.parcelas_pagas = m.parcelas_pagas
    d.contrato_inicio = m.contrato_inicio
    d.contrato_fim = m.contrato_fim
    if m.saldo_devedor > 0:
        d.quitada_em = None
    d.atualizado_em = agora()
    session.add(d)
    return d


def zerar_ausentes(
    session: Session, consentimento_id: int, ids_contas_vistas: set[str], ids_mapeados: set[str], hoje: date
) -> list[Divida]:
    """Dívida cuja conta voltou da Belvo mas não virou dívida (saldo zerado) foi quitada."""
    quitadas = []
    for d in session.exec(select(Divida).where(Divida.consentimento_id == consentimento_id)):
        base = (d.id_externo or "").split(":")[0]
        if d.id_externo not in ids_mapeados and base in ids_contas_vistas and d.saldo_devedor > 0:
            d.saldo_devedor = Decimal("0.00")
            d.quitada_em = hoje
            d.atualizado_em = agora()
            session.add(d)
            quitadas.append(d)
    return quitadas


def dividas(session: Session, usuario_id: int, *, so_abertas: bool = True) -> list[Divida]:
    """Dívidas do usuário, excluindo as de consentimentos revogados."""
    q = (
        select(Divida)
        .join(Consentimento, col(Divida.consentimento_id) == col(Consentimento.id), isouter=True)
        .where(Divida.usuario_id == usuario_id)
        .where(
            (col(Divida.consentimento_id).is_(None))
            | (col(Consentimento.status) != StatusConsentimento.REVOGADO)
        )
    )
    todas = list(session.exec(q))
    return [d for d in todas if d.saldo_devedor > 0] if so_abertas else todas


def divida(session: Session, usuario_id: int, divida_id: int) -> Divida | None:
    d = session.get(Divida, divida_id)
    return d if d and d.usuario_id == usuario_id else None


def salvar_divida(session: Session, d: Divida) -> Divida:
    d.atualizado_em = agora()
    session.add(d)
    session.commit()
    session.refresh(d)
    return d


def apagar_divida(session: Session, d: Divida) -> None:
    session.delete(d)
    session.commit()


def conta_por_externo(session: Session, usuario_id: int, id_externo: str) -> Conta | None:
    return session.exec(
        select(Conta).where(Conta.usuario_id == usuario_id, Conta.id_externo == id_externo)
    ).first()


def contas(session: Session, usuario_id: int) -> list[Conta]:
    return list(session.exec(select(Conta).where(Conta.usuario_id == usuario_id)))


def upsert_transacoes(
    session: Session,
    usuario_id: int,
    consentimento_id: int,
    contas_por_externo: dict[str, int],
    itens: list[TransacaoMapeada],
) -> int:
    existentes = {
        t.id_externo: t
        for t in session.exec(
            select(Transacao).where(col(Transacao.id_externo).in_([i.id_externo for i in itens]))
        )
    }
    for m in itens:
        t = existentes.get(m.id_externo) or Transacao(
            usuario_id=usuario_id, consentimento_id=consentimento_id, id_externo=m.id_externo,
            data_mov=m.data_mov, valor=m.valor,
        )
        t.conta_id_externo = m.conta_id_externo
        t.conta_id = contas_por_externo.get(m.conta_id_externo or "")
        t.data_mov = m.data_mov
        t.transacionado_em = m.transacionado_em
        t.tipo_operacao = m.tipo_operacao
        t.final_cartao = m.final_cartao
        t.fatura_nome = m.fatura_nome
        t.valor = m.valor
        t.direcao = Direcao.ENTRADA if m.valor > 0 else Direcao.SAIDA
        t.descricao = m.descricao
        t.estabelecimento = (m.estabelecimento or None) and m.estabelecimento[:120]
        t.estabelecimento_site = m.estabelecimento_site
        t.subcategoria = (m.subcategoria or None) and m.subcategoria[:80]
        t.categoria = m.categoria
        t.essencial = m.essencial
        t.pagamento_divida = m.pagamento_divida
        t.entrada_renda = m.conta_como_renda
        session.add(t)
    return len(itens)


def transacoes(session: Session, usuario_id: int, desde: date) -> list[Transacao]:
    return list(
        session.exec(
            select(Transacao)
            .join(Consentimento, col(Transacao.consentimento_id) == col(Consentimento.id), isouter=True)
            .where(Transacao.usuario_id == usuario_id, col(Transacao.data_mov) >= desde)
            .where(
                (col(Transacao.consentimento_id).is_(None))
                | (col(Consentimento.status) != StatusConsentimento.REVOGADO)
            )
        )
    )


def adicionar_transacao(session: Session, t: Transacao) -> None:
    session.add(t)


def salvar_renda(
    session: Session, consentimento_id: int, entradas: Decimal | None, essenciais: Decimal | None
) -> None:
    r = session.exec(
        select(RendaDetectada).where(RendaDetectada.consentimento_id == consentimento_id)
    ).first() or RendaDetectada(consentimento_id=consentimento_id)
    if entradas is not None:
        r.entradas_mediana = entradas
    if essenciais is not None:
        r.essenciais_recorrentes = essenciais
    r.atualizado_em = agora()
    session.add(r)
    session.commit()


def rendas(session: Session, usuario_id: int) -> list[RendaDetectada]:
    return list(
        session.exec(
            select(RendaDetectada)
            .join(Consentimento, col(RendaDetectada.consentimento_id) == col(Consentimento.id))
            .where(
                Consentimento.usuario_id == usuario_id,
                Consentimento.status == StatusConsentimento.ATIVO,
            )
        )
    )
