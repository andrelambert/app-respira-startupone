"""Roda a suíte do backend no schema RESPIRA_TESTE, sem exibir senhas.

Uso, na raiz do repositório:  python3 ops/oracle/testes_oracle.py [args do pytest]

Lê RESPIRA_TESTE_PASSWORD e ORACLE_WALLET_PASSWORD de ~/.oracle/respira/segredos.env
e passa ao pytest só pelo ambiente do processo filho. O conftest recusa qualquer
usuário que não termine em _TESTE e começa com o schema de teste vazio
(apaga as tabelas do Respira nele).
"""

import os
import subprocess
import sys
from pathlib import Path

seg = dict(
    linha.split("=", 1)
    for linha in (Path.home() / ".oracle/respira/segredos.env").read_text().splitlines()
    if "=" in linha and not linha.startswith("#")
)
env = {k: v for k, v in os.environ.items() if not k.startswith("ORACLE_")}
env.update(
    {
        "TEST_DATABASE_URL": "oracle+oracledb://@",
        "ORACLE_USER": "RESPIRA_TESTE",
        "ORACLE_PASSWORD": seg["RESPIRA_TESTE_PASSWORD"],
        "ORACLE_DSN": os.environ.get("ORACLE_DSN_TESTE", "respira_tp"),
        "ORACLE_CONFIG_DIR": str(Path.home() / ".oracle/respira/wallet"),
        "ORACLE_WALLET_PASSWORD": seg["ORACLE_WALLET_PASSWORD"],
        "ORACLE_POOL_SIZE": "3",
    }
)
backend = Path(__file__).resolve().parents[2] / "backend"
sys.exit(subprocess.call(["uv", "run", "pytest", "-p", "no:cacheprovider", *sys.argv[1:]], cwd=backend, env=env))
