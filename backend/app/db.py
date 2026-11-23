import logging
from collections.abc import Iterator
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

from app.config import Settings, get_settings

log = logging.getLogger("respira.db")


def _segredo(v: Any) -> str | None:
    return v.get_secret_value() if v is not None else None


def criar_engine(settings: Settings) -> Engine:
    """Engine do SQLite (padrão) ou do Oracle Autonomous AI Database (M2).

    Só este módulo, ``models/`` e ``migrations/`` sabem qual banco está em uso.
    """
    if settings.banco == "oracle":
        if not (settings.oracle_user and settings.oracle_password and settings.oracle_dsn):
            raise RuntimeError("Oracle configurado sem ORACLE_USER, ORACLE_PASSWORD ou ORACLE_DSN.")
        # Modo thin + mTLS: o driver lê tnsnames.ora e ewallet.pem de config_dir.
        eng = create_engine(
            settings.database_url,
            connect_args={
                "user": settings.oracle_user,
                "password": _segredo(settings.oracle_password),
                "dsn": settings.oracle_dsn,
                "config_dir": settings.oracle_config_dir,
                "wallet_location": settings.oracle_config_dir,
                "wallet_password": _segredo(settings.oracle_wallet_password),
            },
            pool_size=settings.oracle_pool_size,  # Always Free: poucas sessões
            max_overflow=2,
            pool_pre_ping=True,
            pool_recycle=1800,  # o ADB derruba conexões ociosas
        )

        @event.listens_for(eng, "connect")
        def _oracle_sessao(dbapi_connection, _):  # pragma: no cover - infraestrutura
            # Datas gravadas e lidas em UTC, como no SQLite (o fuso de negócio,
            # Brasília, é tratado num único lugar do código).
            cursor = dbapi_connection.cursor()
            cursor.execute("ALTER SESSION SET TIME_ZONE = 'UTC'")
            cursor.close()

        # Nunca usuário, senha ou caminho da wallet no log.
        log.info("banco=oracle dsn=%s", settings.oracle_dsn)
        return eng

    eng = create_engine(settings.database_url, connect_args={"check_same_thread": False})

    @event.listens_for(eng, "connect")
    def _sqlite_pragmas(dbapi_connection, _):  # pragma: no cover - infraestrutura
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    log.info("banco=sqlite")
    return eng


engine = criar_engine(get_settings())


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
