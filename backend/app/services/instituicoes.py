"""Catálogo de instituições da Belvo — fonte da verdade de nome e logo dos bancos.

O catálogo quase não muda: é buscado quando está vazio, quando passa de
``REVALIDAR`` desde a última vez, ou na hora em que um banco conectado ainda
não aparece nele. Roda em segundo plano — nunca segura a subida do servidor
nem a conexão do usuário.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlmodel import Session

from app.config import get_settings
from app.db import engine
from app.providers import mapping
from app.providers.base import ErroProvedor
from app.providers.belvo import BelvoProvider
from app.repositories import consentimentos as repo_c
from app.services.contexto import belvo

log = logging.getLogger("respira.instituicoes")

REVALIDAR = timedelta(days=7)
_trava = asyncio.Lock()
_tarefas: set[asyncio.Task[Any]] = set()


def _recente(quando: datetime | None) -> bool:
    if quando is None:
        return False
    quando = quando if quando.tzinfo else quando.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - quando < REVALIDAR


async def sincronizar_catalogo(forcar: bool = False) -> int:
    """Busca o catálogo e grava. Devolve quantas instituições vieram (0 se nada mudou)."""
    if not get_settings().belvo_configurada():
        return 0
    async with _trava:
        with Session(engine) as s:
            if not forcar and _recente(repo_c.ultima_atualizacao_catalogo(s)):
                return 0
        try:
            prov = belvo()
            assert isinstance(prov, BelvoProvider)
            brutos = await prov.listar_instituicoes()
        except ErroProvedor as e:
            log.warning("catalogo_instituicoes_falhou codigo=%s", e.codigo)
            return 0
        catalogo = mapping.mapear_instituicoes(brutos)
        with Session(engine) as s:
            total = repo_c.aplicar_catalogo(s, catalogo)
        log.info("catalogo_instituicoes_atualizado total=%s", total)
        return total


def agendar(forcar: bool = False) -> None:
    tarefa = asyncio.create_task(sincronizar_catalogo(forcar))
    _tarefas.add(tarefa)  # guarda a referência até terminar
    tarefa.add_done_callback(_tarefas.discard)
