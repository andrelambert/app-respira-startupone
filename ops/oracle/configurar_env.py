"""Grava as variáveis do Oracle em backend/.env sem exibir as senhas (trecho da seção 3 do briefing).

Uso, na raiz do repositório:  python3 ops/oracle/configurar_env.py
Mantém as demais linhas do .env (Belvo, demo etc.) e deixa o arquivo com permissão 600.
"""
from pathlib import Path

seg = dict(
    l.split("=", 1)
    for l in (Path.home() / ".oracle/respira/segredos.env").read_text().splitlines()
    if "=" in l and not l.startswith("#")
)
env = Path(__file__).resolve().parents[2] / "backend" / ".env"
linhas = env.read_text().splitlines() if env.exists() else []
novos = {
    "DATABASE_URL": "oracle+oracledb://@",
    "ORACLE_USER": "RESPIRA_APP",
    "ORACLE_PASSWORD": seg["RESPIRA_APP_PASSWORD"],
    "ORACLE_DSN": "respira_tp",
    "ORACLE_CONFIG_DIR": str(Path.home() / ".oracle/respira/wallet"),
    "ORACLE_WALLET_PASSWORD": seg["ORACLE_WALLET_PASSWORD"],
    "ORACLE_REGIAO": "sa-saopaulo-1",
}
fora = [l for l in linhas if l.split("=", 1)[0] not in novos]
env.write_text("\n".join(fora + [f"{k}={v}" for k, v in novos.items()]) + "\n")
env.chmod(0o600)
print("backend/.env atualizado (", ", ".join(novos), ")")
