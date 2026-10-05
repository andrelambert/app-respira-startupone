"""``POST /webhooks/belvo`` (docs/contexto-produto.md §7.5).

Autenticado antes de qualquer processamento, idempotente pelo ``webhook_id``,
responde 2xx rápido e processa em segundo plano.
"""

import hmac
import logging

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, status

from app.config import get_settings
from app.schemas import WebhookEntrada
from app.services import coleta

log = logging.getLogger("respira.webhook")
router = APIRouter(tags=["webhook"])


def _autorizado(authorization: str | None) -> bool:
    token = get_settings().belvo_webhook_token
    if token is None or not token.get_secret_value() or not authorization:
        return False  # sem token configurado, nenhum webhook é aceito
    esperado = f"Bearer {token.get_secret_value()}"
    return hmac.compare_digest(authorization.encode(), esperado.encode())


@router.post("/webhooks/belvo", status_code=status.HTTP_202_ACCEPTED)
async def receber(
    payload: WebhookEntrada,
    tarefas: BackgroundTasks,
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    if not _autorizado(authorization):
        log.warning("webhook_nao_autorizado")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    tarefas.add_task(coleta.processar_webhook, payload.model_dump())
    return {"status": "recebido"}
