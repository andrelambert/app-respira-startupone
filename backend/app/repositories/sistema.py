"""Consulta mínima ao banco para o /health (M3): confirma que ele responde."""

from sqlalchemy import text
from sqlmodel import Session

from app.repositories import oracle as repo_oracle


def versao_do_banco(session: Session, banco: str) -> str | None:
    """Faz uma consulta real (acorda o banco) e devolve a versão. Erro sobe."""
    if banco == "oracle":
        session.exec(text("SELECT 1 FROM dual")).one()  # type: ignore[call-overload]
        return repo_oracle.versao(session)
    return str(session.exec(text("SELECT sqlite_version()")).scalar_one())  # type: ignore[call-overload]
