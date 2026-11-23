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

    # --- Oracle Autonomous AI Database (M2, Fase 7) --------------------------
    # Usado quando database_url começa com "oracle". Modo thin + mTLS pela wallet:
    # só tnsnames.ora e ewallet.pem em oracle_config_dir, sem Instant Client.
    oracle_user: str | None = None
    oracle_password: SecretStr | None = None
    oracle_dsn: str | None = None  # alias do tnsnames.ora, ex.: respira_tp
    oracle_config_dir: str | None = None
    oracle_wallet_password: SecretStr | None = None
    # O Always Free limita sessões simultâneas: pool pequeno.
    oracle_pool_size: int = Field(default=3, ge=1, le=10)
    oracle_regiao: str | None = None
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

    # --- Publicação (M5, Fase 7) ------------------------------------------------
    # Versão pública: vitrine acadêmica. Belvo desligada mesmo que haja chaves,
    # cadastro sem CPF, faixa "não informe dados reais", noindex.
    modo_publico: bool = False
    # "Entrar como Juliana" cria uma Juliana só sua (efêmera), para dois
    # avaliadores não reiniciarem a demo um do outro.
    demo_por_visitante: bool = False
    demo_validade_horas: int = Field(default=24, ge=1, le=168)
    demo_max_ativas: int = Field(default=200, ge=1, le=5000)  # Always Free: espaço e sessões limitados
    demo_por_ip_hora: int = Field(default=10, ge=1, le=1000)

    @property
    def banco(self) -> str:
        """"oracle" ou "sqlite" — o nome do dialeto, nunca a URL."""
        return "oracle" if self.database_url.startswith("oracle") else "sqlite"

    @property
    def cors_origins(self) -> list[str]:
        return [self.app_public_url.rstrip("/")]

    @property
    def cookie_seguro(self) -> bool:
        return self.app_public_url.startswith("https://")

    def belvo_configurada(self) -> bool:
        if self.modo_publico:
            return False  # na versão pública, conexão com banco real fica desligada
        return bool(
            self.belvo_secret_id
            and self.belvo_secret_id.get_secret_value()
            and self.belvo_secret_password
            and self.belvo_secret_password.get_secret_value()
        )

    def demo_configurada(self) -> bool:
        if self.demo_por_visitante:
            return self.demo_habilitada  # não precisa de e-mail/senha fixos
        return bool(self.demo_habilitada and self.demo_email and self.demo_senha)


@lru_cache
def get_settings() -> Settings:
    return Settings()
