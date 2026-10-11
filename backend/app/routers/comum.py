from datetime import timezone
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlmodel import Session

from app.db import get_session
from app.domain.planner import Simulacao, arredondar
from app.domain.xray import DividaXray, juros_do_mes, taxa_anual
from app.models import Consentimento, Divida, Instituicao, StatusColeta, TaxaOrigem, Usuario, agora
from app.repositories import consentimentos as repo_c
from app.repositories import financeiro as repo_f
from app.schemas import ConsentimentoOut, DividaOut, ProjecaoOut, RecursoColetaOut
from app.services import auth
from app.services.conexao import status_efetivo

SessionDep = Annotated[Session, Depends(get_session)]


def usuario_atual(
    s: SessionDep,
    respira_sessao: Annotated[str | None, Cookie()] = None,
) -> Usuario:
    """Toda rota com dado financeiro exige sessão válida — e só enxerga os
    dados do próprio usuário (os repositórios filtram por ``usuario_id``)."""
    u = auth.usuario_do_token(s, respira_sessao)
    if u is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="nao_autenticado")
    return u


UsuarioDep = Annotated[Usuario, Depends(usuario_atual)]


def usuario_demo(u: UsuarioDep) -> Usuario:
    if not u.demo:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="so_conta_demo")
    return u


UsuarioDemoDep = Annotated[Usuario, Depends(usuario_demo)]


def logo(inst: Instituicao | None) -> str | None:
    """Imagem do banco para avatar: o ícone quadrado (``icon_logo``) quando
    existe; senão a marca com texto (``logo``). Ambos do catálogo da Belvo."""
    return (inst.icone_url or inst.logo_url) if inst else None


def divida_out(s: Session, d: Divida) -> DividaOut:
    inst = repo_c.obter_instituicao(s, d.instituicao_id)
    assert d.id is not None
    conta = repo_f.conta_por_externo(s, d.usuario_id, d.conta_id_externo) if d.conta_id_externo else None
    juros = juros_do_mes(
        DividaXray(d.id, d.descricao, d.modalidade, d.saldo_devedor, d.taxa_juros_mes, d.parcela_minima)
    )
    return DividaOut(
        id=d.id,
        descricao=d.descricao,
        instituicao=inst.nome if inst else "",
        modalidade=d.modalidade,
        origem=d.origem,
        saldo=d.saldo_devedor,
        saldo_inicial=d.saldo_inicial,
        taxa_mes=d.taxa_juros_mes,
        taxa_anual=taxa_anual(d.taxa_juros_mes),
        taxa_estimada=d.taxa_origem == TaxaOrigem.ESTIMADA,
        juros_mes=juros,
        parcela_minima=d.parcela_minima,
        parcela_estimada=d.parcela_estimada,
        parcelas_restantes=d.parcelas_restantes,
        dia_vencimento=d.dia_vencimento,
        em_atraso_dias=d.em_atraso_dias,
        quitada_em=d.quitada_em,
        atualizado_em=d.atualizado_em,
        instituicao_logo=logo(inst),
        conta_id=conta.id if conta else None,
        cresce_no_minimo=d.saldo_devedor > 0 and juros > d.parcela_minima,
        valor_contratado=d.valor_contratado,
        parcelas_total=d.parcelas_total,
        parcelas_pagas=d.parcelas_pagas,
        contrato_inicio=d.contrato_inicio,
        contrato_fim=d.contrato_fim,
    )


def projecao_out(sim: Simulacao) -> ProjecaoOut:
    return ProjecaoOut(
        metodo=sim.metodo.value,
        capacidade=sim.capacidade,
        converge=sim.converge,
        meses=sim.meses,
        data_quitacao=sim.data_quitacao,
        juros_totais=arredondar(sim.juros_totais),
        primeira_quitacao_mes=sim.primeira_quitacao_mes,
    )


def consentimento_out(s: Session, c: Consentimento) -> ConsentimentoOut:
    assert c.id is not None
    inst = repo_c.obter_instituicao(s, c.instituicao_id)
    coleta = repo_c.coleta(s, c.id)
    efetivo = status_efetivo(c)
    dias = None
    if c.expira_em:
        exp = c.expira_em if c.expira_em.tzinfo else c.expira_em.replace(tzinfo=timezone.utc)
        dias = (exp - agora()).days
    return ConsentimentoOut(
        id=c.id,
        instituicao=inst.nome if inst else None,
        instituicao_codigo=inst.codigo_externo if inst else None,
        instituicao_logo=logo(inst),
        status=efetivo,
        concedido_em=c.concedido_em,
        expira_em=c.expira_em,
        dias_para_expirar=dias,
        revogado_em=c.revogado_em,
        ultima_sync_em=c.ultima_sync_em,
        erro_codigo=c.erro_codigo,
        coleta=[RecursoColetaOut(recurso=r.recurso, status=r.status) for r in coleta],
        coleta_concluida=bool(coleta) and all(r.status != StatusColeta.AGUARDANDO for r in coleta),
    )
