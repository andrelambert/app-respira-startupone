"""Raio-X (F2), plano (F3) e acompanhamento (F4).

Orquestra domínio + repositórios. Nenhuma regra de cálculo mora aqui — elas
estão em ``domain/`` (planner, xray, events).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Sequence

from sqlmodel import Session

from app.domain import planner
from app.domain.events import EventoDetectado, desvio_plano
from app.domain.planner import (
    DividaEntrada,
    Metodo,
    Movimento,
    Simulacao,
    adicionar_meses,
    arredondar,
    capacidade_de_pagamento,
    medianas_mensais,
)
from app.domain.xray import DividaXray, RaioX, raio_x, taxa_anual
from app.models import (
    Acompanhamento,
    CapacidadeOrigem,
    Direcao,
    Divida,
    MetodoPlano,
    Plano,
    PlanoItem,
    StatusPlano,
    Transacao,
    Usuario,
)
from app.repositories import eventos as repo_e
from app.repositories import financeiro as repo_f
from app.repositories import planos as repo_p
from app.services.coleta import detectar_e_registrar, snapshot
from app.services.contexto import hoje_do_usuario

# Quanto menos entrou no plano num "mês difícil" da demonstração. Precisa
# passar de 20% da capacidade para cruzar a regra de DESVIO_PLANO (< 80%, §8.3).
DEMO_FALTA_MES_DIFICIL = Decimal("240.00")
MESES_REPOSICAO = 3


@dataclass
class Capacidade:
    valor: Decimal
    origem: CapacidadeOrigem
    entradas: Decimal | None
    essenciais: Decimal | None
    meses_historico: int


def capacidade(s: Session, u: Usuario, hoje: date) -> Capacidade:
    """§5.1 / §7.8: renda do add-on INCOMES se houver; senão, mediana das transações."""
    assert u.id is not None
    desde = adicionar_meses(hoje.replace(day=1), -6)
    ts = repo_f.transacoes(s, u.id, desde)
    movs = [Movimento(t.data_mov, t.valor, t.essencial) for t in ts if t.valor < 0 or t.entrada_renda]
    entradas_tx, essenciais, meses = medianas_mensais(movs, hoje)

    rendas = [r.entradas_mediana for r in repo_f.rendas(s, u.id) if r.entradas_mediana is not None]
    if rendas:
        entradas, origem = sum(rendas, Decimal(0)), CapacidadeOrigem.INCOMES
    else:
        entradas, origem = entradas_tx, CapacidadeOrigem.TRANSACOES

    if meses == 0 and not rendas:
        return Capacidade(Decimal("0.00"), CapacidadeOrigem.TRANSACOES, None, None, 0)
    return Capacidade(capacidade_de_pagamento(entradas, essenciais), origem, entradas, essenciais, meses)


def _entradas(dividas: Sequence[Divida]) -> list[DividaEntrada]:
    return [
        DividaEntrada(str(d.id), d.saldo_devedor, d.taxa_juros_mes, d.parcela_minima)
        for d in dividas
        if d.saldo_devedor > 0
    ]


def _xray(dividas: Sequence[Divida]) -> list[DividaXray]:
    return [
        DividaXray(
            id=d.id or 0,
            descricao=d.descricao,
            modalidade=d.modalidade,
            saldo=d.saldo_devedor,
            taxa_mes=d.taxa_juros_mes,
            minima=d.parcela_minima,
            em_atraso_dias=d.em_atraso_dias,
        )
        for d in dividas
    ]


# --- F2 Raio-X ---------------------------------------------------------------


@dataclass
class ResultadoRaioX:
    dividas: list[Divida]
    agregado: RaioX
    capacidade: Capacidade
    metodo: Metodo
    projecao: Simulacao
    capacidade_minima: Decimal | None
    hoje: date


def montar_raio_x(s: Session, u: Usuario) -> ResultadoRaioX:
    assert u.id is not None
    hoje = hoje_do_usuario(u)
    dividas = repo_f.dividas(s, u.id)
    agregado = raio_x(_xray(dividas))
    cap = capacidade(s, u, hoje)
    metodo = planner.metodo_pre_selecionado(u.ja_desistiu_de_plano)
    entradas = _entradas(dividas)
    # A data aparece na mesma tela do diagnóstico (§9 etapa 4): com a
    # capacidade calculada e a estratégia pré-selecionada.
    plano = repo_p.ativo(s, u.id)
    valor = plano.capacidade_mensal if plano else cap.valor
    if plano:
        metodo = Metodo(plano.metodo)
    return ResultadoRaioX(
        dividas=sorted(dividas, key=lambda d: (-d.taxa_juros_mes, d.saldo_devedor, d.id or 0)),
        agregado=agregado,
        capacidade=cap,
        metodo=metodo,
        projecao=planner.simular(entradas, valor, metodo, hoje),
        capacidade_minima=planner.capacidade_minima(entradas, hoje),
        hoje=hoje,
    )


# --- F3 Plano ----------------------------------------------------------------


@dataclass
class ResultadoSimulacoes:
    capacidade: Decimal
    capacidade_calculada: Capacidade
    capacidade_minima: Decimal | None
    compromisso_minimo: Decimal
    pre_selecionado: Metodo
    motivo: str
    simulacoes: dict[Metodo, Simulacao]
    so_minimo: dict[Metodo, planner.CenarioMinimo | None]
    descricoes: dict[str, str]
    hoje: date


def simular(s: Session, u: Usuario, valor: Decimal | None) -> ResultadoSimulacoes:
    assert u.id is not None
    hoje = hoje_do_usuario(u)
    dividas = repo_f.dividas(s, u.id)
    entradas = _entradas(dividas)
    cap = capacidade(s, u, hoje)
    usado = arredondar(valor) if valor is not None else cap.valor
    sims = planner.simular_todas(entradas, usado, hoje)
    # "Só o mínimo" comparado no MESMO horizonte de cada estratégia.
    so_minimo = {
        m: planner.simular_so_minimo(entradas, sim.meses if sim.converge else 24) if entradas else None
        for m, sim in sims.items()
    }
    return ResultadoSimulacoes(
        capacidade=usado,
        capacidade_calculada=cap,
        capacidade_minima=planner.capacidade_minima(entradas, hoje),
        compromisso_minimo=sum((d.minima for d in entradas), Decimal("0.00")),
        pre_selecionado=planner.metodo_pre_selecionado(u.ja_desistiu_de_plano),
        motivo="JA_DESISTIU" if u.ja_desistiu_de_plano else "PADRAO",
        simulacoes=sims,
        so_minimo=so_minimo,
        descricoes={str(d.id): d.descricao for d in dividas},
        hoje=hoje,
    )


class PlanoInviavel(Exception):
    pass


def ativar(s: Session, u: Usuario, metodo: Metodo, valor: Decimal) -> Plano:
    assert u.id is not None
    hoje = hoje_do_usuario(u)
    dividas = repo_f.dividas(s, u.id)
    entradas = _entradas(dividas)
    sim = planner.simular(entradas, valor, metodo, hoje)
    if not sim.converge:
        raise PlanoInviavel()
    so_min = planner.simular_so_minimo(entradas, sim.meses)
    cap = capacidade(s, u, hoje)
    origem = cap.origem if arredondar(valor) == cap.valor else CapacidadeOrigem.USUARIO
    plano = Plano(
        usuario_id=u.id,
        metodo=MetodoPlano(metodo.value),
        capacidade_mensal=sim.capacidade,
        capacidade_origem=origem,
        meses_projetados=sim.meses,
        data_quitacao=sim.data_quitacao,
        juros_totais=sim.juros_totais,
        # Juros que o "só o mínimo" pagaria nos mesmos meses, menos os do plano.
        economia_vs_minimo=so_min.juros_no_horizonte - sim.juros_totais,
        divida_inicial=sum((d.saldo for d in entradas), Decimal("0.00")),
        status=StatusPlano.ATIVO,
        mes_referencia=hoje.replace(day=1),
    )
    itens = [
        PlanoItem(
            plano_id=0,
            divida_id=int(i.divida_id),
            ordem=i.ordem,
            valor_mensal=i.valor_mensal,
            mes_quitacao=i.mes_quitacao,
            juros_pagos=i.juros_pagos,
        )
        for i in sim.itens
    ]
    return repo_p.ativar(s, plano, itens)


@dataclass
class ResultadoPlanoAtivo:
    plano: Plano
    itens: list[PlanoItem]
    projecao: Simulacao
    dividas: dict[int, Divida]
    divida_atual: Decimal
    acompanhamentos: list[Acompanhamento]
    hoje: date


def plano_ativo(s: Session, u: Usuario) -> ResultadoPlanoAtivo | None:
    assert u.id is not None
    plano = repo_p.ativo(s, u.id)
    if plano is None:
        return None
    hoje = hoje_do_usuario(u)
    todas = repo_f.dividas(s, u.id, so_abertas=False)
    abertas = [d for d in todas if d.saldo_devedor > 0]
    # Projeção viva: saldos de hoje, mesma estratégia e capacidade do plano.
    projecao = planner.simular(_entradas(abertas), plano.capacidade_mensal, Metodo(plano.metodo), hoje)
    if not abertas and plano.status == StatusPlano.ATIVO:
        plano.status = StatusPlano.CONCLUIDO
        repo_p.salvar(s, plano)
    assert plano.id is not None
    return ResultadoPlanoAtivo(
        plano=plano,
        itens=repo_p.itens(s, plano.id),
        projecao=projecao,
        dividas={d.id: d for d in todas if d.id is not None},
        divida_atual=sum((d.saldo_devedor for d in abertas), Decimal("0.00")),
        acompanhamentos=repo_p.acompanhamentos(s, plano.id),
        hoje=hoje,
    )


# --- F4 acompanhamento -----------------------------------------------------------


def _registrar_mes(
    s: Session, u: Usuario, plano: Plano, mes: date, realizado: Decimal, data_anterior: date | None
) -> Acompanhamento:
    """Fecha um mês: previsto × realizado, nova data, e DESVIO_PLANO se < 80%."""
    assert u.id is not None and plano.id is not None
    hoje = hoje_do_usuario(u)
    abertas = repo_f.dividas(s, u.id)
    nova = planner.simular(_entradas(abertas), plano.capacidade_mensal, Metodo(plano.metodo), hoje)
    a = repo_p.registrar_acompanhamento(
        s,
        Acompanhamento(
            plano_id=plano.id,
            mes_referencia=mes,
            previsto=plano.capacidade_mensal,
            realizado=realizado,
            data_quitacao_anterior=data_anterior,
            data_quitacao_nova=nova.data_quitacao,
        ),
    )
    if desvio_plano(plano.capacidade_mensal, realizado):
        falta = plano.capacidade_mensal - realizado
        repo_e.registrar_se_novo(
            s,
            u.id,
            EventoDetectado(
                "DESVIO_PLANO",
                f"DP:{plano.id}:{mes:%Y-%m}",
                2,
                None,
                {
                    "mes": mes.isoformat(),
                    "previsto": str(plano.capacidade_mensal),
                    "realizado": str(realizado),
                    "falta": str(falta),
                    "data_anterior": data_anterior.isoformat() if data_anterior else None,
                    "data_nova": nova.data_quitacao.isoformat() if nova.data_quitacao else None,
                    "reposicao_mensal": str(arredondar(falta / MESES_REPOSICAO).to_integral_value()),
                    "meses_reposicao": MESES_REPOSICAO,
                },
            ),
        )
    return a


def recalcular(s: Session, u: Usuario) -> Acompanhamento | None:
    """``POST /plano/recalcular`` — fecha o último mês completo com o que os
    dados mostram (pagamentos de dívida nas transações). Idempotente por mês."""
    assert u.id is not None
    plano = repo_p.ativo(s, u.id)
    if plano is None or plano.id is None:
        return None
    hoje = hoje_do_usuario(u)
    mes = adicionar_meses(hoje.replace(day=1), -1)
    if mes < plano.mes_referencia or repo_p.acompanhamento(s, plano.id, mes):
        return None
    fim = adicionar_meses(mes, 1)
    pagos = sum(
        (-t.valor for t in repo_f.transacoes(s, u.id, mes) if t.pagamento_divida and t.data_mov < fim),
        Decimal("0.00"),
    )
    anteriores = repo_p.acompanhamentos(s, plano.id)
    data_anterior = anteriores[-1].data_quitacao_nova if anteriores else plano.data_quitacao
    return _registrar_mes(s, u, plano, mes, pagos, data_anterior)


def avancar_mes_demo(s: Session, u: Usuario, mes_dificil: bool) -> Acompanhamento:
    """Modo demonstração (fixture): simula um mês de vida real sobre o plano.

    Aplica juros e pagamentos exatamente como o motor (§5.3) e grava as
    transações de pagamento — para que o acompanhamento compare previsto ×
    realizado pelo mesmo caminho do dado real.
    """
    assert u.id is not None
    plano = repo_p.ativo(s, u.id)
    if plano is None or plano.id is None:
        raise PlanoInviavel()
    hoje = hoje_do_usuario(u)
    mes = hoje.replace(day=1)
    abertas = repo_f.dividas(s, u.id)
    anteriores = snapshot(s, u.id)
    pago_no_mes = max(plano.capacidade_mensal - (DEMO_FALTA_MES_DIFICIL if mes_dificil else 0), Decimal(0))

    um_mes = planner.simular(_entradas(abertas), pago_no_mes, Metodo(plano.metodo), hoje)
    pagamentos = {int(i.divida_id): i.valor_mensal for i in um_mes.itens}
    realizado = Decimal("0.00")
    for d in abertas:
        assert d.id is not None
        juros = arredondar(d.saldo_devedor * d.taxa_juros_mes)
        pago = min(pagamentos.get(d.id, Decimal(0)), d.saldo_devedor + juros)
        d.saldo_devedor = max(d.saldo_devedor + juros - pago, Decimal("0.00"))
        if d.saldo_devedor <= planner.SALDO_RESIDUAL:
            d.saldo_devedor = Decimal("0.00")
            d.quitada_em = hoje
        d.em_atraso_dias = 0 if pago >= d.parcela_minima or d.saldo_devedor == 0 else d.em_atraso_dias
        repo_f.salvar_divida(s, d)
        realizado += pago
        if pago > 0:
            repo_f.adicionar_transacao(
                s,
                Transacao(
                    usuario_id=u.id,
                    data_mov=mes.replace(day=min(d.dia_vencimento or 10, 28)),
                    valor=-pago,
                    descricao=f"PAGAMENTO {d.descricao.upper()} (demonstração)",
                    categoria="Credits & Loans",
                    direcao=Direcao.SAIDA,
                    pagamento_divida=True,
                ),
            )

    anteriores_ac = repo_p.acompanhamentos(s, plano.id)
    data_anterior = anteriores_ac[-1].data_quitacao_nova if anteriores_ac else plano.data_quitacao

    u.meses_simulados += 1
    s.add(u)
    s.commit()
    s.refresh(u)

    a = _registrar_mes(s, u, plano, mes, realizado, data_anterior)
    detectar_e_registrar(s, u, hoje_do_usuario(u), anteriores)
    return a


def taxa_anual_de(d: Divida) -> Decimal:
    return taxa_anual(d.taxa_juros_mes)
