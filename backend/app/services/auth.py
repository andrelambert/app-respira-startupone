"""Autenticação: senha com argon2id e sessão opaca em cookie HttpOnly.

* A senha nunca é guardada nem logada — só o hash argon2id.
* O token de sessão é aleatório (256 bits) e vive só no cookie HttpOnly do
  navegador (JavaScript não lê). No banco fica o SHA-256 dele: um vazamento do
  banco não entrega sessões válidas.
* Tentativas de login são limitadas por e-mail para frear força bruta.
"""

from __future__ import annotations

import hashlib
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqlmodel import Session

from app.config import get_settings
from app.models import Usuario
from app.repositories import usuarios as repo_u

COOKIE = "respira_sessao"
MAX_FALHAS = 5
JANELA_FALHAS_S = 15 * 60

_hasher = PasswordHasher()  # argon2id com os parâmetros recomendados da biblioteca
# Hash de referência para gastar o mesmo tempo quando o e-mail não existe
# (não revelar, pelo tempo de resposta, quais e-mails têm conta).
_HASH_FICTICIO = _hasher.hash(secrets.token_urlsafe(16))
_falhas: dict[str, deque[float]] = defaultdict(deque)


class LoginBloqueado(Exception):
    pass


def hash_senha(senha: str) -> str:
    return _hasher.hash(senha)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _bloqueado(email: str) -> bool:
    agora = time.monotonic()
    fila = _falhas[email]
    while fila and agora - fila[0] > JANELA_FALHAS_S:
        fila.popleft()
    return len(fila) >= MAX_FALHAS


def autenticar(s: Session, email: str, senha: str) -> Usuario | None:
    email = email.strip().lower()
    if _bloqueado(email):
        raise LoginBloqueado()
    u = repo_u.por_email(s, email)
    try:
        _hasher.verify(u.senha_hash if u and u.senha_hash else _HASH_FICTICIO, senha)
        ok = u is not None and u.senha_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        ok = False
    if not ok:
        _falhas[email].append(time.monotonic())
        return None
    _falhas.pop(email, None)
    assert u is not None
    if _hasher.check_needs_rehash(u.senha_hash or ""):
        u.senha_hash = hash_senha(senha)
        repo_u.salvar(s, u)
    return u


def abrir_sessao(s: Session, usuario: Usuario) -> tuple[str, int]:
    """Cria a sessão e devolve (token, max_age em segundos) para o cookie."""
    assert usuario.id is not None
    token = secrets.token_urlsafe(32)
    dias = get_settings().sessao_dias
    repo_u.criar_sessao(
        s, usuario.id, _hash_token(token), datetime.now(timezone.utc) + timedelta(days=dias)
    )
    return token, dias * 24 * 3600


def usuario_do_token(s: Session, token: str | None) -> Usuario | None:
    if not token or len(token) > 100:
        return None
    return repo_u.usuario_da_sessao(s, _hash_token(token))


def fechar_sessao(s: Session, token: str | None) -> None:
    if token:
        repo_u.apagar_sessao(s, _hash_token(token))
