"""Conta de demonstração: a Juliana (docs/contexto-produto.md §2), com dados fictícios.

Criada na subida do servidor a partir de ``DEMO_EMAIL``/``DEMO_SENHA`` do
``.env``. Os dados entram pelo MESMO caminho de uma conexão real (token →
widget → callback → coleta → mapeamento), só que servidos pelo FixtureProvider.
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from sqlmodel import Session

from app.config import get_settings
from app.db import engine
from app.models import RECURSOS_ESSENCIAIS, Divida, Origem, TaxaOrigem, TipoInstituicao, Usuario
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
    if not s_cfg.demo_configurada():
        return
    assert s_cfg.demo_email and s_cfg.demo_senha
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


async def semear(s: Session, u: Usuario) -> None:
    assert u.id is not None
    for codigo in BANCOS_DEMO:
        _, url = await conexao.iniciar(s, u)
        token = url.split("access_token=")[1].split("&")[0]
        link = fixture().autorizar(token, codigo)
        c = await conexao.concluir(s, u, link, codigo, iniciar_coleta=False)
        assert c.id is not None
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
