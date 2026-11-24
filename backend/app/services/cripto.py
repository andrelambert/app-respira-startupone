"""CPF criptografado em repouso (M6, Fase 7 — §8 do briefing, LGPD).

- ``usuario.cpf`` guarda um token Fernet (AES-128-CBC + HMAC-SHA256), nunca o número.
- ``usuario.cpf_hash`` guarda um HMAC-SHA256 do CPF com uma chave derivada da
  mesma ``CPF_CHAVE``: permite saber se o CPF já está em uso sem decifrar nada.
- A chave vem só do ambiente (``CPF_CHAVE``; no Render, variável secreta). Sem
  ela, o app não grava CPF (o cadastro com Belvo recusa) — nunca em texto puro.
- O CPF decifrado só existe em memória, no momento de montar o token da Belvo.
  Nunca vai para log.
"""

from __future__ import annotations

import hashlib
import hmac
import re

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


class ChaveAusente(Exception):
    """CPF_CHAVE não configurada."""


def _chave() -> bytes:
    k = get_settings().cpf_chave
    if k is None or not k.get_secret_value():
        raise ChaveAusente()
    return k.get_secret_value().encode()


def configurada() -> bool:
    try:
        Fernet(_chave())
        return True
    except (ChaveAusente, ValueError):
        return False


def _hmac_chave() -> bytes:
    # Chave separada para o HMAC, derivada da mesma CPF_CHAVE (não reutiliza o material da cifra).
    return hashlib.sha256(b"respira-cpf-hash:" + _chave()).digest()


def eh_texto_puro(valor: str | None) -> bool:
    """CPF gravado antes da criptografia: 11 dígitos."""
    return bool(valor) and re.fullmatch(r"\d{11}", valor or "") is not None


def cifrar(cpf: str) -> str:
    return Fernet(_chave()).encrypt(cpf.encode()).decode()


def decifrar(valor: str | None) -> str | None:
    if not valor:
        return None
    if eh_texto_puro(valor):
        return valor  # legado, ainda não cifrado (a subida cifra)
    try:
        return Fernet(_chave()).decrypt(valor.encode()).decode()
    except (ChaveAusente, InvalidToken):
        return None  # chave trocada ou ausente: trata como sem CPF, nunca quebra a tela


def hash_cpf(cpf: str) -> str:
    return hmac.new(_hmac_chave(), cpf.encode(), hashlib.sha256).hexdigest()
