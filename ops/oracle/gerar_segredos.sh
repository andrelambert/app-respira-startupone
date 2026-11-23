#!/usr/bin/env bash
# Gera as senhas do Respira no Oracle e grava em ~/.oracle/respira/segredos.env (permissão 600).
# As senhas NUNCA aparecem na tela nem no histórico do terminal.
# Uso: bash gerar_segredos.sh            (não sobrescreve se o arquivo já existir)
set -euo pipefail

DIR="$HOME/.oracle/respira"
ARQ="$DIR/segredos.env"
mkdir -p "$DIR"
chmod 700 "$HOME/.oracle" "$DIR"

if [[ -f "$ARQ" ]]; then
  echo "Já existe $ARQ — nada foi alterado. Apague-o à mão se quiser gerar senhas novas."
  exit 0
fi

# Regras do Autonomous: 12 a 30 caracteres, com maiúscula, minúscula e número, sem aspas e sem o
# nome do usuário. Usamos só letras e números (24 caracteres) para não ter problema de escape.
gerar() {
  python3 - <<'PY'
import secrets, string
alf = string.ascii_letters + string.digits
while True:
    s = ''.join(secrets.choice(alf) for _ in range(24))
    if any(c.islower() for c in s) and any(c.isupper() for c in s) and sum(c.isdigit() for c in s) >= 2:
        print(s); break
PY
}

umask 177
cat > "$ARQ" <<EOF
# Segredos do Respira no Oracle — NUNCA commitar, NUNCA colar no chat.
ADB_ADMIN_PASSWORD=$(gerar)
RESPIRA_APP_PASSWORD=$(gerar)
RESPIRA_TESTE_PASSWORD=$(gerar)
ORACLE_WALLET_PASSWORD=$(gerar)
EOF
chmod 600 "$ARQ"
echo "Senhas geradas em $ARQ (permissão 600)."
echo "Para ver a senha do ADMIN (vai precisar dela no console ao criar o banco):"
echo "  grep ADB_ADMIN_PASSWORD $ARQ"
