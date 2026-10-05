"""Configuração lida do ambiente / ``backend/.env`` (docs/contexto-produto.md §7.0 e §12).

Nenhum segredo tem valor padrão aqui. ``.env`` nunca entra no Git.
"""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_public_url: str = "http://localhost:5173"
    app_terms_url: str = "https://exemplo.com/termos"
    database_url: str = "sqlite:///./respira.db"
    log_level: str = "INFO"
    sessao_dias: int = Field(default=7, ge=1, le=30)

    # --- Belvo (contas reais) ------------------------------------------------
    belvo_base_url: str = "https://api.belvo.com"  # produção
    belvo_secret_id: SecretStr | None = None
    belvo_secret_password: SecretStr | None = None
    belvo_widget_url: str = "https://widget.belvo.io"
    belvo_webhook_token: SecretStr | None = None
    # Sem túnel público não chega webhook em localhost (§7.5): coleta por polling.
    belvo_webhooks_enabled: bool = False
    belvo_stale_in: str = "300d"
    # Add-ons INCOMES / RECURRING_EXPENSES (§7.6). Ligados: se a conta Belvo não
    # os tiver habilitados e o token falhar por isso, desligue aqui.
    belvo_enrichment_enabled: bool = True

    # --- Conta de demonstração (Juliana, dados fictícios) ---------------------
    # As credenciais da demo vêm do .env, não do código (§12.3). Sem elas, a
    # Juliana não é criada.
    demo_habilitada: bool = True
    demo_email: str | None = None
    demo_senha: SecretStr | None = None
    # Atraso entre os webhooks simulados da fixture.
    fixture_coleta_segundos: float = Field(default=2.0, ge=0)

    @property
    def cors_origins(self) -> list[str]:
        return [self.app_public_url.rstrip("/")]

    @property
    def cookie_seguro(self) -> bool:
        return self.app_public_url.startswith("https://")

    def belvo_configurada(self) -> bool:
        return bool(
            self.belvo_secret_id
            and self.belvo_secret_id.get_secret_value()
            and self.belvo_secret_password
            and self.belvo_secret_password.get_secret_value()
        )

    def demo_configurada(self) -> bool:
        return bool(self.demo_habilitada and self.demo_email and self.demo_senha)


@lru_cache
def get_settings() -> Settings:
    return Settings()
