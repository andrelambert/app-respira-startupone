"""Coleta: provedor → mapeamento → repositórios → eventos (docs/contexto-produto.md §7.5).

Três gatilhos chegam aqui:

* webhook real da Belvo (``POST /webhooks/belvo``);
* polling de fallback quando não há túnel para webhook (``BELVO_WEBHOOKS_ENABLED=false``);
* webhooks simulados da fixture, que passam pelo **mesmo** pipeline
  (``webhook_log``, deduplicação, processamento).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlmodel import Session

from app.config import get_settings
from app.db import engine
from app.domain.events import DividaEstado, GastoCategoria, detectar
from app.domain.planner import adicionar_meses
from app.models import (
    RECURSOS_ESSENCIAIS,
    TIPOS_CONTA_DEPOSITO,
    Consentimento,
    Divida,
    Recurso,
    StatusColeta,
    StatusConsentimento,
    TipoInstituicao,
    Usuario,
    WebhookLog,
)
from app.providers import mapping
from app.providers.base import ErroProvedor, RecursoIndisponivel
from app.repositories import consentimentos as repo_c
from app.repositories import eventos as repo_e
from app.repositories import financeiro as repo_f
from app.services.contexto import hoje_do_usuario, provider

log = logging.getLogger("respira.coleta")

# SQLite + tarefas concorrentes: serializar a escrita é simples e suficiente
# nesta escala (um usuário local).
_trava = asyncio.Lock()
_tarefas: dict[int, asyncio.Task[Any]] = {}

POLLING_INTERVALO_S = 10
# Banco real pode levar alguns minutos para a coleta histórica (12 meses).
POLLING_LIMITE = timedelta(minutes=10)
MESES_DE_TRANSACOES = 12

WEBHOOK_TIPO_RECURSO = {
    "OWNERS": Recurso.OWNERS,
    "ACCOUNTS": Recurso.ACCOUNTS,
    "TRANSACTIONS": Recurso.TRANSACTIONS,
    "BILLS": Recurso.BILLS,
    "INCOMES": Recurso.INCOMES,
    "RECURRING_EXPENSES": Recurso.RECURRING_EXPENSES,
}


# --- snapshot para detecção de eventos -----------------------------------------


def _estado(d: Divida, nome_inst: str) -> DividaEstado:
    assert d.id is not None
    return DividaEstado(
        id=d.id,
        descricao=d.descricao,
        instituicao=nome_inst,
        modalidade=d.modalidade,
        saldo=d.saldo_devedor,
        taxa_mes=d.taxa_juros_mes,
        minima=d.parcela_minima,
        dia_vencimento=d.dia_vencimento,
        em_atraso_dias=d.em_atraso_dias,
    )


def snapshot(s: Session, usuario_id: int) -> dict[int, DividaEstado]:
    out = {}
    for d in repo_f.dividas(s, usuario_id, so_abertas=False):
        inst = repo_c.obter_instituicao(s, d.instituicao_id)
        out[d.id] = _estado(d, inst.nome if inst else "")  # type: ignore[index]
    return out


def detectar_e_registrar(
    s: Session, usuario: Usuario, hoje: date, anteriores: dict[int, DividaEstado]
) -> int:
    assert usuario.id is not None
    atuais = list(snapshot(s, usuario.id).values())
    # Só conta corrente/poupança/pagamento: "dinheiro na conta" para pagar a parcela.
    contas = [c for c in repo_f.contas(s, usuario.id) if c.tipo in TIPOS_CONTA_DEPOSITO]
    saldo_em_conta = sum((c.saldo for c in contas), Decimal(0)) if contas else None
    usado_cheque = sum(
        (d.saldo for d in atuais if d.modalidade == "CHEQUE_ESPECIAL" and d.saldo > 0), Decimal(0)
    )
    desde = adicionar_meses(hoje.replace(day=1), -8)
    gastos = [
        GastoCategoria(t.data_mov, t.categoria, -t.valor)
        for t in repo_f.transacoes(s, usuario.id, desde)
        if t.valor < 0 and t.categoria and not t.pagamento_divida
    ]
    novos = 0
    for e in detectar(
        hoje=hoje,
        dividas=atuais,
        anteriores=anteriores,
        saldo_em_conta=saldo_em_conta,
        usado_cheque_especial=usado_cheque,
        gastos=gastos,
    ):
        if repo_e.registrar_se_novo(s, usuario.id, e):
            novos += 1
    return novos


# --- processamento de um recurso ---------------------------------------------------


async def processar_recurso(consentimento_id: int, recurso: Recurso, *, confirmar_vazio: bool) -> int:
    """Busca o recurso, persiste e detecta eventos. Devolve quantos itens vieram.

    ``confirmar_vazio``: no caminho do webhook, a Belvo já avisou que a coleta
    terminou — zero itens é resposta válida. No polling, zero pode ser "ainda
    não chegou", então o recurso continua AGUARDANDO.
    """
    async with _trava:
        with Session(engine) as s:
            c = s.get(Consentimento, consentimento_id)
            if c is None or c.status != StatusConsentimento.ATIVO or not c.link_externo:
                return 0
            usuario = s.get(Usuario, c.usuario_id)
            assert usuario is not None and usuario.id is not None
            hoje = hoje_do_usuario(usuario)
            if usuario.demo and usuario.meses_simulados:
                # Com o relógio de demonstração adiantado, os saldos já foram
                # movidos pela simulação; recoletar a fixture os voltaria ao início.
                repo_c.marcar_recurso(s, consentimento_id, recurso, StatusColeta.RECEBIDO)
                return 0
            anteriores = snapshot(s, usuario.id)
            try:
                if recurso in (Recurso.ACCOUNTS, Recurso.BILLS):
                    qtd = await _contas_e_faturas(s, c, usuario, hoje, recurso)
                elif recurso is Recurso.TRANSACTIONS:
                    qtd = await _transacoes(s, c, usuario, hoje)
                elif recurso in (Recurso.INCOMES, Recurso.RECURRING_EXPENSES):
                    qtd = await _enriquecimento(s, c, usuario, recurso)
                else:
                    # OWNERS: não lemos nome/CPF/e-mail do titular — minimização (§12.7).
                    qtd = 1
            except RecursoIndisponivel:
                repo_c.marcar_recurso(s, consentimento_id, recurso, StatusColeta.INDISPONIVEL)
                return 0
            except ErroProvedor as e:
                log.warning("coleta_falhou consentimento=%s recurso=%s codigo=%s", c.id, recurso, e.codigo)
                repo_c.marcar_recurso(s, consentimento_id, recurso, StatusColeta.ERRO)
                return 0

            if qtd > 0 or confirmar_vazio:
                repo_c.marcar_recurso(s, consentimento_id, recurso, StatusColeta.RECEBIDO)
            repo_c.marcar_sync(s, c)
            detectar_e_registrar(s, usuario, hoje, anteriores)
            return qtd


async def _contas_e_faturas(
    s: Session, c: Consentimento, usuario: Usuario, hoje: date, recurso: Recurso
) -> int:
    """Contas e faturas são mapeadas juntas: a modalidade do cartão depende da
    fatura (§7.7). Quem chegar primeiro mapeia com o que houver; o segundo
    reconcilia por upsert."""
    assert c.id and c.link_externo and usuario.id
    prov = provider(usuario)
    contas = await prov.listar(Recurso.ACCOUNTS, c.link_externo)
    faturas = await prov.listar(Recurso.BILLS, c.link_externo)
    inst = repo_c.obter_instituicao(s, c.instituicao_id)
    if inst is None:
        nome = mapping.instituicao_da_conta(contas[0]).nome if contas else "Instituição"
        inst = repo_c.instituicao(s, f"desconhecida_{c.id}", nome, TipoInstituicao.BANCO)
        c.instituicao_id = inst.id
    elif contas and inst.nome == inst.codigo_externo:
        inst.nome = mapping.instituicao_da_conta(contas[0]).nome
    assert inst.id is not None

    r = mapping.mapear_contas(contas, faturas, hoje, inst.codigo_externo, inst.nome)
    ids_contas: dict[str, int] = {}
    for m in r.contas:
        conta = repo_f.upsert_conta(s, usuario.id, c.id, inst.id, m)
        s.flush()
        assert conta.id is not None
        ids_contas[m.id_externo] = conta.id
    for f in r.faturas:
        if f.conta_id_externo in ids_contas:
            repo_f.upsert_fatura(s, usuario.id, c.id, ids_contas[f.conta_id_externo], f)
    for d in r.dividas:
        repo_f.upsert_divida(s, usuario.id, c.id, inst.id, d)
    vistas = {a["id"] for a in contas if a.get("id")}
    repo_f.zerar_ausentes(s, c.id, vistas, {d.id_externo for d in r.dividas}, hoje)
    s.commit()

    # Sem cartão de crédito, não há fatura a esperar.
    if contas and not any(a.get("category") == "CREDIT_CARD" for a in contas):
        repo_c.marcar_recurso(s, c.id, Recurso.BILLS, StatusColeta.RECEBIDO)
    return len(contas) if recurso is Recurso.ACCOUNTS else len(faturas)


async def _transacoes(s: Session, c: Consentimento, usuario: Usuario, hoje: date) -> int:
    assert c.id and c.link_externo and usuario.id
    desde = adicionar_meses(hoje.replace(day=1), -MESES_DE_TRANSACOES)
    brutas = await provider(usuario).listar(Recurso.TRANSACTIONS, c.link_externo, desde=desde, ate=hoje)
    itens = mapping.mapear_transacoes(brutas)
    contas = {k.id_externo: k.id for k in repo_f.contas(s, usuario.id) if k.id}
    repo_f.upsert_transacoes(s, usuario.id, c.id, contas, itens)
    s.commit()
    return len(itens)


async def _enriquecimento(s: Session, c: Consentimento, usuario: Usuario, recurso: Recurso) -> int:
    assert c.id and c.link_externo
    itens = await provider(usuario).listar(recurso, c.link_externo)
    if recurso is Recurso.INCOMES:
        repo_f.salvar_renda(s, c.id, mapping.entradas_de_incomes(itens), None)
    else:
        repo_f.salvar_renda(s, c.id, None, mapping.essenciais_recorrentes(itens))
    return len(itens)


# --- webhooks -----------------------------------------------------------------------


async def processar_webhook(payload: dict[str, Any]) -> None:
    """Pipeline do webhook. Idempotente pelo ``webhook_id``."""
    webhook_id = str(payload.get("webhook_id") or "")
    with Session(engine) as s:
        novo = repo_e.registrar_webhook(
            s,
            WebhookLog(
                webhook_id=webhook_id,
                webhook_type=str(payload.get("webhook_type") or "")[:40],
                webhook_code=str(payload.get("webhook_code") or "")[:60],
                process_type=(payload.get("process_type") or None),
                link_id=payload.get("link_id"),
                request_id=payload.get("request_id"),
                external_id=payload.get("external_id"),
            ),
        )
        if not novo:
            return
        c = repo_c.por_link(s, payload.get("link_id") or "")
        consentimento_id = c.id if c else None

    erro = None
    try:
        if consentimento_id is None:
            erro = "link_desconhecido"
        else:
            erro = await _despachar(consentimento_id, payload)
    except Exception as e:  # noqa: BLE001 — o log precisa registrar qualquer falha
        log.exception("webhook_falhou webhook_id=%s", webhook_id)
        erro = type(e).__name__
    with Session(engine) as s:
        repo_e.concluir_webhook(s, webhook_id, erro)


async def _despachar(consentimento_id: int, payload: dict[str, Any]) -> str | None:
    tipo = str(payload.get("webhook_type") or "").upper()
    codigo = str(payload.get("webhook_code") or "")
    dados = payload.get("data") or {}

    if tipo in WEBHOOK_TIPO_RECURSO:
        if dados.get("errors"):
            with Session(engine) as s:
                repo_c.marcar_recurso(s, consentimento_id, WEBHOOK_TIPO_RECURSO[tipo], StatusColeta.ERRO)
            return "erro_reportado_pela_belvo"
        await processar_recurso(consentimento_id, WEBHOOK_TIPO_RECURSO[tipo], confirmar_vazio=True)
        return None

    with Session(engine) as s:
        c = s.get(Consentimento, consentimento_id)
        assert c is not None
        if codigo == "openfinance_consent_expired":
            c.status = StatusConsentimento.EXPIRADO
        elif codigo == "openfinance_consent_about_to_expire":
            c.expira_em = _data_hora(dados.get("consent_due_date")) or c.expira_em
        elif codigo == "openfinance_consent_expiration_changed":
            c.expira_em = _data_hora(dados.get("new_expiration"))
        elif codigo == "consent_rejected":
            c.status = StatusConsentimento.ERRO
            c.erro_codigo = "consent_rejected"
        elif codigo == "link_deleted":
            repo_c.apagar_dados_do_link(s, c)
            return None
        elif codigo in {"invalid_credentials", "token_required"}:
            c.status = StatusConsentimento.ERRO
            c.erro_codigo = codigo
        else:
            return f"codigo_ignorado:{codigo}"[:60]
        repo_c.salvar(s, c)
    return None


def _data_hora(valor: Any) -> datetime | None:
    if not valor:
        return None
    try:
        return datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except ValueError:
        return None


# --- orquestração da coleta -----------------------------------------------------------


def iniciar(consentimento_id: int) -> None:
    """Dispara a coleta adequada ao provedor/configuração, sem duplicar tarefa."""
    atual = _tarefas.get(consentimento_id)
    if atual and not atual.done():
        return
    s = get_settings()
    with Session(engine) as sessao:
        c = sessao.get(Consentimento, consentimento_id)
        dono = sessao.get(Usuario, c.usuario_id) if c else None
        demo = bool(dono and dono.demo)
    if demo:
        corrotina = _simular_webhooks(consentimento_id, s.fixture_coleta_segundos)
    elif s.belvo_webhooks_enabled:
        corrotina = _aguardar_webhooks(consentimento_id)
    else:
        corrotina = _polling(consentimento_id)
    _tarefas[consentimento_id] = asyncio.create_task(corrotina)


async def _simular_webhooks(consentimento_id: int, atraso: float) -> None:
    with Session(engine) as s:
        c = s.get(Consentimento, consentimento_id)
        if c is None or not c.link_externo:
            return
        link, usuario = c.link_externo, s.get(Usuario, c.usuario_id)
    for recurso in (Recurso.OWNERS, Recurso.ACCOUNTS, Recurso.BILLS, Recurso.TRANSACTIONS):
        await asyncio.sleep(atraso)
        await processar_webhook(
            {
                "webhook_id": f"fixture-{uuid.uuid4()}",
                "webhook_type": recurso.value,
                "webhook_code": "historical_update",
                "process_type": "historical_update",
                "link_id": link,
                "request_id": None,
                "external_id": usuario.uuid_externo if usuario else None,
                "data": {},
            }
        )


async def _aguardar_webhooks(consentimento_id: int) -> None:
    """Com webhook configurado, só marca como indisponível o que não chegou no prazo."""
    await asyncio.sleep(POLLING_LIMITE.total_seconds())
    _expirar_pendentes(consentimento_id)


async def _polling(consentimento_id: int) -> None:
    """Fallback sem túnel (§7.5): tenta os recursos até chegarem ou o prazo acabar."""
    limite = datetime.now() + POLLING_LIMITE
    while datetime.now() < limite:
        with Session(engine) as s:
            pendentes = [
                r.recurso for r in repo_c.coleta(s, consentimento_id) if r.status == StatusColeta.AGUARDANDO
            ]
        if not pendentes:
            return
        for recurso in pendentes:
            await processar_recurso(consentimento_id, recurso, confirmar_vazio=False)
        await asyncio.sleep(POLLING_INTERVALO_S)
    _expirar_pendentes(consentimento_id)


def _expirar_pendentes(consentimento_id: int) -> None:
    with Session(engine) as s:
        for r in repo_c.coleta(s, consentimento_id):
            if r.status == StatusColeta.AGUARDANDO:
                repo_c.marcar_recurso(s, consentimento_id, r.recurso, StatusColeta.INDISPONIVEL)


async def sincronizar_tudo(usuario_id: int) -> int:
    """``POST /sync``: força a recoleta de todos os links ativos (fallback manual)."""
    with Session(engine) as s:
        ids = [c.id for c in repo_c.listar(s, usuario_id) if c.status == StatusConsentimento.ATIVO]
    total = 0
    for cid in ids:
        assert cid is not None
        for recurso in (*RECURSOS_ESSENCIAIS,):
            total += await processar_recurso(cid, recurso, confirmar_vazio=True)
    return total
