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
    CategoriaGastoOut,
    ContaDetalheOut,
    ContaOut,
    ExtratoOut,
    FaturaOut,
    FluxoMensalOut,
    FluxoMesOut,
    GastoMesOut,
    GastosCategoriaOut,
    GastoSubcategoriaOut,
    HistoricoCategoriaOut,
    ImpactoPlanoOut,
    PagamentoFaturaOut,
    TodasTransacoesOut,
    TransacaoOut,
    TransacaoUnificadaOut,
    VencimentoOut,
    VencimentosOut,
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


# --- N1 (Fase 7): todas as transações -------------------------------------------------

MAX_ITENS_LISTA = 20


def _lista_ints(valor: str | None, nome: str) -> tuple[int, ...]:
    if not valor:
        return ()
    partes = [p.strip() for p in valor.split(",") if p.strip()]
    if len(partes) > MAX_ITENS_LISTA or not all(p.isdigit() and len(p) <= 9 for p in partes):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{nome}_invalido")
    return tuple(int(p) for p in partes)


def _lista_textos(valor: str | None, nome: str) -> tuple[str, ...]:
    if not valor:
        return ()
    partes = [p.strip() for p in valor.split(",") if p.strip()]
    if len(partes) > MAX_ITENS_LISTA or any(len(p) > 80 for p in partes):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{nome}_invalido")
    return tuple(partes)


@router.get("/transacoes", response_model=TodasTransacoesOut)
def todas_transacoes(
    u: UsuarioDep,
    s: SessionDep,
    pagina: Annotated[int, Query(ge=1, le=10_000)] = 1,
    por_pagina: Annotated[int, Query(ge=5, le=100)] = 30,
    desde: date | None = None,
    ate: date | None = None,
    contas: Annotated[str | None, Query(max_length=200, description="ids separados por vírgula")] = None,
    direcao: Literal["ENTRADA", "SAIDA"] | None = None,
    categorias: Annotated[str | None, Query(max_length=1700, description="nomes separados por vírgula")] = None,
    busca: Annotated[str | None, Query(max_length=60)] = None,
    valor_min: Annotated[Decimal | None, Query(ge=0, le=Decimal("1000000000"))] = None,
    valor_max: Annotated[Decimal | None, Query(ge=0, le=Decimal("1000000000"))] = None,
    so_divida: bool = False,
    fluxo: Literal["renda", "gasto"] | None = None,
    tipo_conta: Literal["CORRENTE", "CARTAO", "POUPANCA", "INVESTIMENTOS"] | None = None,
    ordem: Literal["recentes", "maior_valor"] = "recentes",
) -> TodasTransacoesOut:
    """Extrato unificado de todas as contas e cartões, com filtros (N1, F-1/F-2)."""
    assert u.id is not None
    if desde and ate and desde > ate:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "periodo_invalido")
    if desde and ate and (ate - desde).days > 3660:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "periodo_longo_demais")
    if valor_min is not None and valor_max is not None and valor_min > valor_max:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "faixa_de_valor_invalida")
    filtro = repo.FiltroTransacoes(
        desde=desde,
        ate=ate,
        contas=_lista_ints(contas, "contas"),
        direcao=Direcao(direcao) if direcao else None,
        categorias=_lista_textos(categorias, "categorias"),
        busca=(busca or "").strip() or None,
        valor_min=valor_min,
        valor_max=valor_max,
        so_divida=so_divida,
        fluxo=fluxo,
        tipo_conta=tipo_conta,
        ordem=ordem,
    )
    itens, total, entradas, saidas = repo.transacoes_filtradas(s, u.id, filtro, pagina=pagina, por_pagina=por_pagina)

    # Banco e nome da conta de cada transação (só as contas do próprio usuário).
    origem: dict[int, tuple[str | None, str | None, str | None]] = {}
    for c in repo.contas(s, u.id):
        inst = repo_c.obter_instituicao(s, c.instituicao_id)
        nome = c.nome or None
        origem[c.id or 0] = (inst.nome if inst else None, logo(inst), nome)
    return TodasTransacoesOut(
        itens=[
            TransacaoUnificadaOut(
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
                data_compra=t.data_compra,
                parcela_numero=t.parcela_numero,
                parcelas_total=t.parcelas_total,
                conta_id=t.conta_id,
                banco=origem.get(t.conta_id or -1, (None, None, None))[0],
                banco_logo=origem.get(t.conta_id or -1, (None, None, None))[1],
                conta_nome=origem.get(t.conta_id or -1, (None, None, None))[2],
                pagamento_divida=t.pagamento_divida,
            )
            for t in itens
        ],
        pagina=pagina,
        por_pagina=por_pagina,
        total=total,
        paginas=max(1, -(-total // por_pagina)),
        total_entradas=entradas,
        total_saidas=saidas,
        resultado=entradas - saidas,
    )


@router.get("/pfm/categorias", response_model=GastosCategoriaOut)
def gastos_por_categoria(
    u: UsuarioDep,
    s: SessionDep,
    mes: Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM")] = None,
) -> GastosCategoriaOut:
    """Para onde foi o dinheiro (N2, F-3/F-4), ligado ao plano."""
    from app.services import analise

    alvo = date(int(mes[:4]), int(mes[5:]), 1) if mes else None
    m, cats, impacto, meses = analise.gastos_por_categoria(s, u, alvo)
    return GastosCategoriaOut(
        mes=m,
        meses_disponiveis=meses[-12:],
        categorias=[
            CategoriaGastoOut(
                categoria=c.categoria, total=c.total, media_3m=c.media_3m, variacao=c.variacao, essencial=c.essencial
            )
            for c in cats
        ],
        total=sum((c.total for c in cats), Decimal("0.00")),
        impacto_plano=ImpactoPlanoOut(**impacto.__dict__) if impacto else None,
    )


@router.get("/pfm/categorias/historico", response_model=HistoricoCategoriaOut)
def historico_categoria(
    u: UsuarioDep,
    s: SessionDep,
    categoria: Annotated[str, Query(min_length=1, max_length=80)],
    meses: Annotated[int, Query(ge=3, le=12)] = 12,
    subcategoria: Annotated[str | None, Query(max_length=80)] = None,
) -> HistoricoCategoriaOut:
    """Detalhe de uma categoria de gasto: evolução (da categoria ou de uma
    subcategoria) e as subcategorias para filtrar."""
    from app.services import analise

    serie, subs = analise.historico_categoria(s, u, categoria, meses, subcategoria)
    return HistoricoCategoriaOut(
        categoria=categoria,
        meses=[GastoMesOut(mes=m, total=v) for m, v in serie],
        subcategorias=[GastoSubcategoriaOut(subcategoria=n, total=v) for n, v in subs],
    )


@router.get("/pfm/fluxo-mensal", response_model=FluxoMensalOut)
def fluxo_mensal(u: UsuarioDep, s: SessionDep, meses: Annotated[int, Query(ge=3, le=12)] = 6) -> FluxoMensalOut:
    """Entradas × gastos × dívida, mês a mês, e a conta da capacidade (N5, F-7)."""
    from app.domain.planner import FATOR_RESERVA
    from app.services import analise

    fluxo, cap = analise.fluxo_mensal(s, u, meses)
    return FluxoMensalOut(
        meses=[FluxoMesOut(**f.__dict__) for f in fluxo],
        capacidade=cap.valor,
        capacidade_origem=cap.origem.value,
        entradas_mediana=cap.entradas,
        essenciais_mediana=cap.essenciais,
        reserva_pct=int((1 - FATOR_RESERVA) * 100),
    )


@router.get("/vencimentos", response_model=VencimentosOut)
def vencimentos(u: UsuarioDep, s: SessionDep, dias: Annotated[int, Query(ge=1, le=60)] = 30) -> VencimentosOut:
    """Próximos vencimentos (N3, F-5): faturas e parcelas na janela, e os atrasados."""
    from app.services import analise

    hoje, itens = analise.vencimentos(s, u, dias)
    return VencimentosOut(
        hoje=hoje,
        dias=dias,
        itens=[
            VencimentoOut(
                data=v.data, tipo=v.tipo, credor=v.credor, descricao=v.descricao, valor=v.valor,  # type: ignore[arg-type]
                valor_total=v.valor_total, valor_plano=plano, status=v.status.value, dias=v.dias,  # type: ignore[arg-type]
                divida_id=v.divida_id, conta_id=v.conta_id, banco_logo=logo,
            )
            for v, plano, logo in itens
        ],
    )


@router.get("/transacoes/categorias", response_model=list[str])
def categorias_das_transacoes(u: UsuarioDep, s: SessionDep) -> list[str]:
    """Categorias que existem nas transações do usuário (nomes da Belvo; a tela traduz)."""
    assert u.id is not None
    return repo.categorias_usadas(s, u.id)


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
                data_compra=t.data_compra,
                parcela_numero=t.parcela_numero,
                parcelas_total=t.parcelas_total,
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
