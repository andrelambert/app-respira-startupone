"""Raio-X (F2), dívidas, plano (F3) e acompanhamento (F4)."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.domain.planner import Metodo, arredondar
from app.models import (
    Divida,
    Origem,
    StatusColeta,
    StatusConsentimento,
    TaxaOrigem,
    TipoInstituicao,
)
from app.repositories import consentimentos as repo_c
from app.repositories import financeiro as repo_f
from app.routers.comum import SessionDep, UsuarioDep, divida_out, projecao_out
from app.schemas import (
    AcompanhamentoOut,
    CapacidadeOut,
    DividaAtualizar,
    DividaCriar,
    DividaOut,
    EstrategiaOut,
    ItemPlanoOut,
    PagamentoMesOut,
    PlanoAtivar,
    PlanoAtivoOut,
    RaioXOut,
    SimulacoesOut,
    SoMinimoOut,
)
from app.services import analise
from app.services.analise import Capacidade

router = APIRouter(tags=["diagnóstico e plano"])


def _cap(c: Capacidade) -> CapacidadeOut:
    return CapacidadeOut(
        valor=c.valor,
        origem=c.origem,
        entradas=c.entradas,
        essenciais=c.essenciais,
        meses_historico=c.meses_historico,
    )


# --- F2 -----------------------------------------------------------------------------


@router.get("/raiox", response_model=RaioXOut)
def raiox(u: UsuarioDep, s: SessionDep) -> RaioXOut:
    assert u.id is not None
    r = analise.montar_raio_x(s, u)
    ag = r.agregado
    consentimentos = [c for c in repo_c.listar(s, u.id) if c.status == StatusConsentimento.ATIVO]
    em_andamento = any(
        item.status == StatusColeta.AGUARDANDO
        for c in consentimentos
        for item in repo_c.coleta(s, c.id)  # type: ignore[arg-type]
    )
    syncs = [c.ultima_sync_em for c in consentimentos if c.ultima_sync_em]
    por_id = {d.id: d for d in r.dividas}
    renda = r.capacidade.entradas
    comprometimento = arredondar(ag.compromisso_minimo_mes / renda * 100) if renda and renda > 0 else None
    maior = por_id.get(ag.maior_fonte_juros_id)
    return RaioXOut(
        coleta_em_andamento=em_andamento,
        atualizado_em=min(syncs) if syncs else None,
        qtd_dividas=ag.qtd_dividas,
        divida_total=ag.divida_total,
        juros_mes_estimado=ag.juros_mes_estimado,
        compromisso_minimo_mes=ag.compromisso_minimo_mes,
        pior_taxa_anual=ag.pior_taxa_anual,
        qtd_em_atraso=ag.qtd_em_atraso,
        divida_cresce=ag.divida_cresce,
        crescimento_mensal=ag.crescimento_mensal,
        maior_fonte_juros=divida_out(s, maior) if maior else None,
        maior_fonte_juros_valor=ag.maior_fonte_juros_valor,
        comprometimento_renda_pct=comprometimento,
        capacidade=_cap(r.capacidade),
        capacidade_minima=r.capacidade_minima,
        projecao=projecao_out(r.projecao),
        dividas=[divida_out(s, d) for d in r.dividas],
    )


# --- dívidas (cadastro manual assistido, §7.9) ---------------------------------------------


@router.get("/dividas", response_model=list[DividaOut])
def listar_dividas(u: UsuarioDep, s: SessionDep, quitadas: bool = False) -> list[DividaOut]:
    assert u.id is not None
    return [divida_out(s, d) for d in repo_f.dividas(s, u.id, so_abertas=not quitadas)]


@router.post("/dividas", response_model=DividaOut, status_code=status.HTTP_201_CREATED)
def criar_divida(dados: DividaCriar, u: UsuarioDep, s: SessionDep) -> DividaOut:
    from app.content.taxas_referencia import taxa_estimada
    from app.services.coleta import detectar_e_registrar, snapshot
    from app.services.contexto import hoje_do_usuario

    assert u.id is not None
    codigo = "manual_" + "".join(ch if ch.isalnum() else "_" for ch in dados.credor.lower())[:60]
    tipo = TipoInstituicao.CREDIARIO if dados.modalidade == "CREDIARIO" else TipoInstituicao.OUTRO
    inst = repo_c.instituicao(s, codigo, dados.credor, tipo)
    anteriores = snapshot(s, u.id)
    informada = dados.taxa_mes_percentual is not None
    taxa = (dados.taxa_mes_percentual / 100) if informada else taxa_estimada(dados.modalidade)  # type: ignore[operator]
    descricoes = {"CREDIARIO": "Carnê", "OUTRO": "Dívida"}
    d = repo_f.salvar_divida(
        s,
        Divida(
            usuario_id=u.id,
            instituicao_id=inst.id,  # type: ignore[arg-type]
            modalidade=dados.modalidade,
            descricao=f"{descricoes.get(dados.modalidade, 'Dívida')} {dados.credor}",
            saldo_devedor=dados.saldo,
            saldo_inicial=dados.saldo,
            taxa_juros_mes=taxa,
            taxa_origem=TaxaOrigem.INFORMADA if informada else TaxaOrigem.ESTIMADA,
            parcela_minima=dados.parcela,
            dia_vencimento=dados.dia_vencimento,
            em_atraso_dias=dados.em_atraso_dias,
            origem=Origem.MANUAL,
        ),
    )
    detectar_e_registrar(s, u, hoje_do_usuario(u), anteriores)
    return divida_out(s, d)


@router.patch("/dividas/{divida_id}", response_model=DividaOut)
def atualizar_divida(divida_id: int, dados: DividaAtualizar, u: UsuarioDep, s: SessionDep) -> DividaOut:
    """Correções que o Open Finance não entrega (parcela/taxa estimadas). Saldo
    só é editável em dívida manual — o de Open Finance vem do banco."""
    assert u.id is not None
    d = repo_f.divida(s, u.id, divida_id)
    if d is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if dados.saldo is not None:
        if d.origem != Origem.MANUAL:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="saldo_vem_do_banco")
        d.saldo_devedor = dados.saldo
    if dados.parcela is not None:
        d.parcela_minima = dados.parcela
        d.parcela_estimada = False
    if dados.taxa_mes_percentual is not None:
        d.taxa_juros_mes = dados.taxa_mes_percentual / 100
        d.taxa_origem = TaxaOrigem.INFORMADA
    if dados.dia_vencimento is not None:
        d.dia_vencimento = dados.dia_vencimento
    return divida_out(s, repo_f.salvar_divida(s, d))


@router.delete("/dividas/{divida_id}", status_code=status.HTTP_204_NO_CONTENT)
def apagar_divida(divida_id: int, u: UsuarioDep, s: SessionDep) -> None:
    assert u.id is not None
    d = repo_f.divida(s, u.id, divida_id)
    if d is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if d.origem != Origem.MANUAL:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="revogue_a_conexao")
    repo_f.apagar_divida(s, d)


# --- F3 -------------------------------------------------------------------------------


@router.get("/plano/simulacoes", response_model=SimulacoesOut)
def simulacoes(
    u: UsuarioDep,
    s: SessionDep,
    capacidade: Annotated[Decimal | None, Query(gt=0, le=Decimal("1000000"))] = None,
) -> SimulacoesOut:
    r = analise.simular(s, u, capacidade)
    estrategias = []
    for metodo in (Metodo.AVALANCHE, Metodo.EQUILIBRADO, Metodo.SNOWBALL):
        sim = r.simulacoes[metodo]
        m = r.so_minimo[metodo]
        estrategias.append(
            EstrategiaOut(
                **projecao_out(sim).model_dump(),
                itens=[
                    ItemPlanoOut(
                        divida_id=int(i.divida_id),
                        descricao=r.descricoes.get(i.divida_id, ""),
                        ordem=i.ordem,
                        valor_mensal=i.valor_mensal,
                        mes_quitacao=i.mes_quitacao,
                        juros_pagos=i.juros_pagos,
                    )
                    for i in sim.itens
                ],
                trajetoria=[arredondar(v) for v in sim.trajetoria[:241]],
                so_minimo=SoMinimoOut(
                    converge=m.converge,
                    meses=m.meses,
                    juros_no_horizonte=m.juros_no_horizonte,
                    saldo_no_horizonte=m.saldo_no_horizonte,
                )
                if m
                else None,
            )
        )
    return SimulacoesOut(
        capacidade=r.capacidade,
        capacidade_calculada=_cap(r.capacidade_calculada),
        capacidade_minima=r.capacidade_minima,
        compromisso_minimo_mes=r.compromisso_minimo,
        pre_selecionado=r.pre_selecionado.value,
        motivo_pre_selecao=r.motivo,  # type: ignore[arg-type]
        estrategias=estrategias,
    )


def _plano_ativo_out(s: SessionDep, r: analise.ResultadoPlanoAtivo) -> PlanoAtivoOut:
    p = r.plano
    assert p.id is not None
    abatido = max(p.divida_inicial - r.divida_atual, Decimal("0.00"))
    progresso = arredondar(abatido / p.divida_inicial * 100) if p.divida_inicial > 0 else Decimal("100")

    def inst(d: Divida) -> str:
        i = repo_c.obter_instituicao(s, d.instituicao_id)
        return i.nome if i else ""

    este_mes = []
    for item in r.projecao.itens:
        d = r.dividas.get(int(item.divida_id))
        if d is None or item.valor_mensal <= 0:
            continue
        este_mes.append(
            PagamentoMesOut(
                divida_id=d.id or 0,
                descricao=d.descricao,
                instituicao=inst(d),
                valor=item.valor_mensal,
                dia_vencimento=d.dia_vencimento,
                ordem=item.ordem,
                e_minimo=item.valor_mensal <= d.parcela_minima,
            )
        )
    return PlanoAtivoOut(
        id=p.id,
        metodo=p.metodo,
        status=p.status,
        capacidade_mensal=p.capacidade_mensal,
        capacidade_origem=p.capacidade_origem,
        criado_em=p.criado_em,
        meses_projetados=p.meses_projetados,
        data_quitacao_original=p.data_quitacao,
        juros_totais_original=p.juros_totais,
        economia_vs_minimo=p.economia_vs_minimo,
        divida_inicial=p.divida_inicial,
        divida_atual=r.divida_atual,
        abatido=abatido,
        progresso_pct=progresso,
        projecao_atual=projecao_out(r.projecao),
        este_mes=este_mes,
        cronograma=[
            ItemPlanoOut(
                divida_id=i.divida_id,
                descricao=r.dividas[i.divida_id].descricao if i.divida_id in r.dividas else "",
                ordem=i.ordem,
                valor_mensal=i.valor_mensal,
                mes_quitacao=i.mes_quitacao,
                juros_pagos=i.juros_pagos,
            )
            for i in r.itens
        ],
        acompanhamentos=[
            AcompanhamentoOut(
                mes_referencia=a.mes_referencia,
                previsto=a.previsto,
                realizado=a.realizado,
                data_quitacao_anterior=a.data_quitacao_anterior,
                data_quitacao_nova=a.data_quitacao_nova,
            )
            for a in r.acompanhamentos
        ],
        hoje=r.hoje,
    )


@router.post("/plano", response_model=PlanoAtivoOut, status_code=status.HTTP_201_CREATED)
def ativar(dados: PlanoAtivar, u: UsuarioDep, s: SessionDep) -> PlanoAtivoOut:
    try:
        analise.ativar(s, u, Metodo(dados.metodo), dados.capacidade)
    except analise.PlanoInviavel as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="plano_nao_converge") from e
    r = analise.plano_ativo(s, u)
    assert r is not None
    return _plano_ativo_out(s, r)


@router.get("/plano/ativo", response_model=PlanoAtivoOut)
def plano_ativo(u: UsuarioDep, s: SessionDep) -> PlanoAtivoOut:
    r = analise.plano_ativo(s, u)
    if r is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="sem_plano")
    return _plano_ativo_out(s, r)


@router.post("/plano/recalcular", response_model=PlanoAtivoOut)
def recalcular(u: UsuarioDep, s: SessionDep) -> PlanoAtivoOut:
    analise.recalcular(s, u)
    r = analise.plano_ativo(s, u)
    if r is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="sem_plano")
    return _plano_ativo_out(s, r)
