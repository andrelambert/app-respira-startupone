"""PFM — finanças pessoais sobre os dados do banco: contas, saldos, faturas e
extrato. Funciona para quem não tem dívida nenhuma."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import Session

from app.domain.pfm import em_aberto, horario_brasil, situacao_fatura
from app.models import TIPOS_CONTA_DEPOSITO, Conta, Direcao, Fatura, StatusConsentimento, TipoConta
from app.repositories import consentimentos as repo_c
from app.repositories import financeiro as repo_f
from app.repositories import pfm as repo
from app.routers.comum import SessionDep, UsuarioDep, consentimento_out, logo
from app.schemas import (
    BancoOut,
    ContaDetalheOut,
    ContaOut,
    ExtratoOut,
    FaturaOut,
    PagamentoFaturaOut,
    TransacaoOut,
    VisaoGeralOut,
)
from app.services.contexto import hoje_do_usuario

router = APIRouter(tags=["PFM"])

ORDEM_TIPOS = [
    "CORRENTE", "POUPANCA", "PAGAMENTO", "CARTAO_CREDITO", "ADIANTAMENTO", "EMPRESTIMO", "FINANCIAMENTO", "OUTRO",
]


def _fatura_out(f: Fatura, hoje: date) -> FaturaOut:
    assert f.id is not None
    return FaturaOut(
        id=f.id,
        nome=f.nome,
        vencimento=f.vencimento,
        total=f.total,
        minimo=f.minimo,
        pago=f.pago,
        em_aberto=em_aberto(f.total, f.pago),
        encargos=f.encargos,
        parcelada=f.parcelada,
        situacao=situacao_fatura(f.total, f.minimo, f.pago, f.vencimento, hoje).value,
        pagamentos=[PagamentoFaturaOut.model_validate(p) for p in f.pagamentos or []],
    )


def _conta_out(s: Session, c: Conta, hoje: date) -> ContaOut:
    assert c.id is not None
    inst = repo_c.obter_instituicao(s, c.instituicao_id)
    atual = None
    if c.tipo == TipoConta.CARTAO_CREDITO:
        fs = repo.faturas(s, c.id)
        atual = _fatura_out(fs[0], hoje) if fs else None
    return ContaOut(
        id=c.id,
        consentimento_id=c.consentimento_id,
        instituicao=inst.nome if inst else "",
        instituicao_logo=logo(inst),
        tipo=c.tipo,
        nome=c.nome,
        numero_final=c.numero_final,
        tipo_externo=c.tipo_externo,
        agencia=c.agencia,
        numero_conta=c.numero_conta,
        saldo=c.saldo,
        disponivel=c.disponivel,
        limite_credito=c.limite_credito,
        limite_cheque_especial=c.limite_cheque_especial,
        usado_cheque_especial=c.usado_cheque_especial,
        fatura_atual=atual,
        atualizado_em=c.atualizado_em,
    )


@router.get("/pfm/visao-geral", response_model=VisaoGeralOut)
def visao_geral(u: UsuarioDep, s: SessionDep) -> VisaoGeralOut:
    assert u.id is not None
    hoje = hoje_do_usuario(u)
    bancos: list[BancoOut] = []
    saldo, faturas = Decimal("0.00"), Decimal("0.00")
    for c in repo_c.listar(s, u.id):
        if c.status == StatusConsentimento.REVOGADO:
            continue
        assert c.id is not None
        # Conta corrente primeiro, depois poupança, cartão e crédito.
        contas = sorted(
            (_conta_out(s, conta, hoje) for conta in repo.contas(s, u.id, c.id)),
            key=lambda x: (ORDEM_TIPOS.index(x.tipo) if x.tipo in ORDEM_TIPOS else 99, x.id),
        )
        for conta in contas:
            if conta.tipo in TIPOS_CONTA_DEPOSITO:
                saldo += conta.saldo
            if conta.fatura_atual and conta.fatura_atual.situacao != "PAGA":
                faturas += conta.fatura_atual.em_aberto
        info = consentimento_out(s, c)
        bancos.append(
            BancoOut(
                consentimento_id=c.id,
                instituicao=info.instituicao,
                instituicao_codigo=info.instituicao_codigo,
                instituicao_logo=info.instituicao_logo,
                status=info.status,
                ultima_sync_em=info.ultima_sync_em,
                expira_em=info.expira_em,
                coleta_concluida=info.coleta_concluida,
                coleta=info.coleta,
                contas=contas,
            )
        )
    return VisaoGeralOut(
        bancos=bancos,
        saldo_em_contas=saldo,
        faturas_em_aberto=faturas,
        qtd_dividas=len(repo_f.dividas(s, u.id)),
        hoje=hoje,
    )


def _conta_do_usuario(s: Session, usuario_id: int, conta_id: int) -> Conta:
    c = repo.conta(s, usuario_id, conta_id)
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="conta_nao_encontrada")
    return c


@router.get("/contas/{conta_id}", response_model=ContaDetalheOut)
def detalhe(conta_id: int, u: UsuarioDep, s: SessionDep) -> ContaDetalheOut:
    assert u.id is not None
    c = _conta_do_usuario(s, u.id, conta_id)
    hoje = hoje_do_usuario(u)
    assert c.id is not None
    return ContaDetalheOut(conta=_conta_out(s, c, hoje), faturas=[_fatura_out(f, hoje) for f in repo.faturas(s, c.id)])


@router.get("/contas/{conta_id}/transacoes", response_model=ExtratoOut)
def extrato(
    conta_id: int,
    u: UsuarioDep,
    s: SessionDep,
    pagina: Annotated[int, Query(ge=1, le=10_000)] = 1,
    por_pagina: Annotated[int, Query(ge=5, le=100)] = 20,
    direcao: Literal["ENTRADA", "SAIDA"] | None = None,
    busca: Annotated[str | None, Query(max_length=60)] = None,
    desde: date | None = None,
    ate: date | None = None,
    dias: Annotated[int | None, Query(ge=1, le=3650)] = None,  # últimos N dias
) -> ExtratoOut:
    assert u.id is not None
    c = _conta_do_usuario(s, u.id, conta_id)
    assert c.id is not None
    if dias is not None:
        desde = hoje_do_usuario(u) - timedelta(days=dias)
    itens, total, entradas, saidas = repo.transacoes_paginadas(
        s,
        u.id,
        c.id,
        pagina=pagina,
        por_pagina=por_pagina,
        direcao=Direcao(direcao) if direcao else None,
        busca=(busca or "").strip() or None,
        desde=desde,
        ate=ate,
    )
    return ExtratoOut(
        itens=[
            TransacaoOut(
                id=t.id or 0,
                data=t.data_mov,
                transacionado_em=horario_brasil(t.transacionado_em) if t.transacionado_em else None,
                tipo_operacao=t.tipo_operacao,
                final_cartao=t.final_cartao,
                fatura=t.fatura_nome,
                descricao=t.descricao,
                estabelecimento=t.estabelecimento,
                estabelecimento_site=t.estabelecimento_site,
                categoria=t.categoria,
                subcategoria=t.subcategoria,
                valor=t.valor,
                direcao=t.direcao.value,
            )
            for t in itens
        ],
        pagina=pagina,
        por_pagina=por_pagina,
        total=total,
        paginas=max(1, -(-total // por_pagina)),
        total_entradas=entradas,
        total_saidas=saidas,
    )
