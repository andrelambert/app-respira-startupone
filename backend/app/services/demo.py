"""Conta de demonstração: a Juliana (docs/contexto-produto.md §2), com dados fictícios.

Criada na subida do servidor a partir de ``DEMO_EMAIL``/``DEMO_SENHA`` do
``.env``. Os dados entram pelo MESMO caminho de uma conexão real (token →
widget → callback → coleta → mapeamento), só que servidos pelo FixtureProvider.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import timedelta
from decimal import Decimal

from sqlmodel import Session

from app.config import get_settings
from app.db import engine
from app.models import (
    RECURSOS_ESSENCIAIS,
    Divida,
    Origem,
    TaxaOrigem,
    TipoInstituicao,
    Usuario,
    agora,
)
from app.providers.fixture import BANCOS_DA_JULIANA
from app.repositories import consentimentos as repo_c
from app.repositories import financeiro as repo_f
from app.repositories import usuarios as repo_u
from app.services import auth, coleta, conexao
from app.services.contexto import fixture, hoje_do_usuario

log = logging.getLogger("respira.demo")

BANCOS_DEMO = BANCOS_DA_JULIANA


async def garantir_juliana() -> None:
    s_cfg = get_settings()
    # A Juliana fixa (uso local) precisa de e-mail e senha; na versão pública
    # (DEMO_POR_VISITANTE) cada visitante ganha a sua e ela não existe.
    if not (s_cfg.demo_habilitada and s_cfg.demo_email and s_cfg.demo_senha):
        return
    email = s_cfg.demo_email.strip().lower()
    senha = s_cfg.demo_senha.get_secret_value()
    with Session(engine) as s:
        u = repo_u.por_email(s, email)
        if u is not None and not u.demo:
            log.warning("demo_email_em_uso_por_conta_real — conta demo não criada")
            return
        if u is None:
            u = repo_u.criar(
                s,
                Usuario(
                    uuid_externo=str(uuid.uuid4()),
                    email=email,
                    senha_hash=auth.hash_senha(senha),
                    demo=True,
                    apelido="Juliana",
                    nome_completo="Juliana Ramos",  # persona fictícia
                    ja_desistiu_de_plano=False,
                ),
            )
        elif auth.autenticar(s, email, senha) is None:
            # A senha da demo mudou no .env: acompanha.
            u.senha_hash = auth.hash_senha(senha)
            repo_u.salvar(s, u)
        assert u.id is not None
        consentimentos = repo_c.listar(s, u.id)
        bancos = {
            inst.codigo_externo
            for c in consentimentos
            if c.status == "ATIVO" and (inst := repo_c.obter_instituicao(s, c.instituicao_id))
        }
        if not consentimentos:
            await semear(s, u)
        elif bancos != set(BANCOS_DEMO):
            # A fixture mudou de bancos (ou um foi revogado): reprocessar os
            # consentimentos antigos zeraria as contas. Recomeça a demo do zero.
            log.info("demo_bancos_mudaram -> reiniciando")
            await reiniciar(s, u)
        elif not u.meses_simulados:
            # Reprocessa os dados fictícios: upsert idempotente, mantém o plano,
            # e faz mudanças no mapeamento chegarem à demo já existente.
            for c in consentimentos:
                if c.id is not None and c.status == "ATIVO":
                    for recurso in RECURSOS_ESSENCIAIS:
                        await coleta.processar_recurso(c.id, recurso, confirmar_vazio=True)


async def semear(s: Session, u: Usuario, *, coletar_em_segundo_plano: bool = False) -> None:
    """``coletar_em_segundo_plano``: a demo por visitante (M5) não espera a coleta
    — os três bancos ficam "conectados" na hora e os dados chegam pela mesma
    coleta de uma conexão real, com a tela de espera do Raio-X. Contra o Oracle
    em São Paulo, esperar tudo levava ~10 s no clique de "Entrar como Juliana"."""
    assert u.id is not None
    for codigo in BANCOS_DEMO:
        _, url = await conexao.iniciar(s, u)
        token = url.split("access_token=")[1].split("&")[0]
        link = fixture().autorizar(token, codigo)
        c = await conexao.concluir(s, u, link, codigo, iniciar_coleta=coletar_em_segundo_plano)
        assert c.id is not None
        if not coletar_em_segundo_plano:
            for recurso in RECURSOS_ESSENCIAIS:
                await coleta.processar_recurso(c.id, recurso, confirmar_vazio=True)

    # O carnê da Loja D não trafega pelo Open Finance: cadastro manual (§7.9).
    inst = repo_c.instituicao(s, "manual_loja_d", "Loja D", TipoInstituicao.CREDIARIO)
    assert inst.id is not None
    anteriores = coleta.snapshot(s, u.id)
    repo_f.salvar_divida(
        s,
        Divida(
            usuario_id=u.id,
            instituicao_id=inst.id,
            modalidade="CREDIARIO",
            descricao="Carnê Loja D",
            saldo_devedor=Decimal("380.00"),
            saldo_inicial=Decimal("380.00"),
            taxa_juros_mes=Decimal("0.035"),
            taxa_origem=TaxaOrigem.INFORMADA,
            parcela_minima=Decimal("95.00"),
            dia_vencimento=15,
            em_atraso_dias=12,
            origem=Origem.MANUAL,
        ),
    )
    coleta.detectar_e_registrar(s, u, hoje_do_usuario(u), anteriores)
    log.info("demo_semeada")


async def reiniciar(s: Session, u: Usuario) -> None:
    """Volta a Juliana ao estado inicial (para a próxima apresentação)."""
    assert u.demo and u.id is not None
    repo_u.apagar_dados_financeiros(s, u.id)
    u.meses_simulados = 0
    repo_u.salvar(s, u)
    await semear(s, u)


# --- demo por visitante (M5, Fase 7) --------------------------------------------------


class DemosEsgotadas(Exception):
    """Limite de demos ativas atingido (o Always Free tem espaço e sessões limitados)."""


async def criar_demo_visitante(s: Session) -> Usuario:
    """Uma Juliana só deste visitante, apagada com todos os dados depois de
    ``DEMO_VALIDADE_HORAS``. Os ids da fixture são por link, então várias
    Julianas convivem sem colidir."""
    cfg = get_settings()
    if repo_u.demos_ativas(s, agora()) >= cfg.demo_max_ativas:
        raise DemosEsgotadas()
    u = repo_u.criar(
        s,
        Usuario(
            uuid_externo=str(uuid.uuid4()),
            email=f"demo+{uuid.uuid4().hex[:16]}@respira.example",
            senha_hash=None,  # ninguém entra com senha: só pelo cookie desta sessão
            demo=True,
            apelido="Juliana",
            nome_completo="Juliana Ramos",  # persona fictícia
            ja_desistiu_de_plano=False,
            expira_em=agora() + timedelta(hours=cfg.demo_validade_horas),
        ),
    )
    assert u.id is not None
    # A semeadura (3 bancos, carnê, ~400 comandos no banco) vai para segundo
    # plano: do Render ao Oracle em São Paulo ela leva dezenas de segundos, e o
    # visitante esperava isso no clique — a Vercel desistia antes (502). Agora
    # o login volta na hora e o Raio-X mostra a espera com o progresso.
    preparando.add(u.id)
    tarefa = asyncio.create_task(asyncio.to_thread(_semear_em_thread, u.id))
    _tarefas.add(tarefa)
    tarefa.add_done_callback(_tarefas.discard)
    log.info("demo_visitante_criada")
    return u


# Demos sendo preparadas agora (uma instância só no Render): o Raio-X mostra a
# espera da coleta enquanto o usuário estiver aqui, mesmo antes dos bancos existirem.
preparando: set[int] = set()
_tarefas: set[asyncio.Task] = set()


def _semear_em_thread(usuario_id: int) -> None:
    try:
        with Session(engine) as s:
            u = s.get(Usuario, usuario_id)
            if u is not None:
                asyncio.run(semear(s, u))
    except Exception:  # falha numa demo não derruba o servidor
        log.exception("demo_visitante_semeadura_falhou")
    finally:
        preparando.discard(usuario_id)


def apagar_demos_expiradas() -> int:
    """Apaga demos efêmeras vencidas com tudo o que é delas. Roda na subida e a cada hora."""
    with Session(engine) as s:
        ids = repo_u.demos_expiradas(s, agora())
        for i in ids:
            repo_u.apagar_tudo(s, i)
    if ids:
        log.info("demos_expiradas_apagadas qtd=%s", len(ids))
    return len(ids)
