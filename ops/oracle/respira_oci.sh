#!/usr/bin/env bash
# Operações do Respira na Oracle Cloud pela OCI CLI.
# Pré-requisitos: oci-cli instalada e sessão aberta com
#   oci session authenticate --region sa-saopaulo-1 --profile-name respira
#
# Uso:
#   bash respira_oci.sh sessao        valida a sessão (renova se ainda estiver dentro das 24 h)
#   bash respira_oci.sh criar-compartimento   cria o compartimento "respira" na raiz da conta
#   bash respira_oci.sh criar-banco   cria o Autonomous AI Database Always Free (alternativa ao console)
#   bash respira_oci.sh descobrir     acha o compartimento e o banco e grava os ids em ~/.oracle/respira/ids.env
#   bash respira_oci.sh estado        mostra nome, estado, versão e região do banco
#   bash respira_oci.sh ligar         liga o banco e espera ficar AVAILABLE
#   bash respira_oci.sh desligar      desliga o banco (o Always Free não cobra; use só se precisar)
#   bash respira_oci.sh wallet        baixa a wallet e deixa só tnsnames.ora e ewallet.pem em ~/.oracle/respira/wallet
#   bash respira_oci.sh rotacionar    rotaciona a wallet (invalida as antigas) — pede confirmação
#
# Nunca imprime senhas. Os ids (OCIDs) não são segredo, mas não precisam aparecer em prints.
set -euo pipefail

PERFIL="${OCI_PERFIL:-respira}"
REGIAO="${OCI_REGIAO:-sa-saopaulo-1}"
DIR="$HOME/.oracle/respira"
IDS="$DIR/ids.env"
SEG="$DIR/segredos.env"
COMPARTIMENTO_NOME="${COMPARTIMENTO_NOME:-respira}"

oci_() { oci --profile "$PERFIL" --auth security_token --region "$REGIAO" "$@"; }
carregar_ids() { [[ -f "$IDS" ]] || { echo "Rode primeiro: bash $0 descobrir"; exit 1; }; source "$IDS"; }
senha_wallet() { [[ -f "$SEG" ]] || { echo "Falta $SEG (rode gerar_segredos.sh)"; exit 1; }; grep '^ORACLE_WALLET_PASSWORD=' "$SEG" | cut -d= -f2-; }

case "${1:-}" in
  sessao)
    if ! oci session validate --profile "$PERFIL" --auth security_token >/dev/null 2>&1; then
      echo "Sessão expirada. Rode no terminal (abre o navegador):"
      echo "  oci session authenticate --region $REGIAO --profile-name $PERFIL"
      exit 1
    fi
    oci session refresh --profile "$PERFIL" >/dev/null 2>&1 || true
    echo "Sessão OCI válida (perfil $PERFIL)." ;;

  criar-compartimento)
    TENANCY=$(awk -v p="[$PERFIL]" '$0==p{f=1;next} /^\[/{f=0} f && /^tenancy=/{sub("tenancy=","");print}' "$HOME/.oci/config")
    oci_ iam compartment create --compartment-id "$TENANCY" --name "$COMPARTIMENTO_NOME" \
      --description "Respira - Startup One / Enterprise Challenge" --wait-for-state ACTIVE \
      --query 'data.name' --raw-output ;;

  criar-banco)
    # Alternativa ao console. Se a CLI recusar algum parâmetro (as opções do Always Free mudam com
    # o tempo), crie pelo console seguindo o guia e depois rode "descobrir".
    TENANCY=$(awk -v p="[$PERFIL]" '$0==p{f=1;next} /^\[/{f=0} f && /^tenancy=/{sub("tenancy=","");print}' "$HOME/.oci/config")
    COMP=$(oci_ iam compartment list --compartment-id "$TENANCY" --all \
            --query "data[?name=='$COMPARTIMENTO_NOME' && \"lifecycle-state\"=='ACTIVE'].id | [0]" --raw-output 2>/dev/null || true)
    [[ -n "$COMP" && "$COMP" != "null" ]] || COMP="$TENANCY"
    [[ -f "$SEG" ]] || { echo "Falta $SEG (rode gerar_segredos.sh)"; exit 1; }
    ADMIN_PW=$(grep '^ADB_ADMIN_PASSWORD=' "$SEG" | cut -d= -f2-)
    EXTRA=()
    [[ -n "${DB_VERSAO:-}" ]] && EXTRA+=(--db-version "$DB_VERSAO")
    oci_ db autonomous-database create --compartment-id "$COMP" \
      --db-name RESPIRA --display-name Respira --db-workload OLTP \
      --is-free-tier true --cpu-core-count 1 --data-storage-size-in-tbs 1 \
      --admin-password "$ADMIN_PW" --is-mtls-connection-required true ${EXTRA[@]+"${EXTRA[@]}"} \
      --wait-for-state AVAILABLE --max-wait-seconds 1800 \
      --query 'data.{nome:"display-name", estado:"lifecycle-state", versao:"db-version"}' --output table
    unset ADMIN_PW
    echo "Agora rode: bash $0 descobrir" ;;

  descobrir)
    mkdir -p "$DIR"; chmod 700 "$DIR"
    TENANCY=$(awk -v p="[$PERFIL]" '$0==p{f=1;next} /^\[/{f=0} f && /^tenancy=/{sub("tenancy=","");print}' "$HOME/.oci/config")
    [[ -n "$TENANCY" ]] || { echo "Não achei o tenancy no perfil $PERFIL de ~/.oci/config"; exit 1; }
    COMP=$(oci_ iam compartment list --compartment-id "$TENANCY" --all \
            --query "data[?name=='$COMPARTIMENTO_NOME' && \"lifecycle-state\"=='ACTIVE'].id | [0]" --raw-output 2>/dev/null || true)
    if [[ -z "$COMP" || "$COMP" == "null" ]]; then
      echo "Compartimento '$COMPARTIMENTO_NOME' não existe; usando o compartimento raiz (tenancy)."
      COMP="$TENANCY"
    fi
    ADB=$(oci_ db autonomous-database list --compartment-id "$COMP" --all \
            --query "data[?\"lifecycle-state\"!='TERMINATED'].id | [0]" --raw-output)
    [[ -n "$ADB" && "$ADB" != "null" ]] || { echo "Nenhum Autonomous Database encontrado no compartimento."; exit 1; }
    umask 177
    printf 'TENANCY_ID=%s\nCOMPARTMENT_ID=%s\nADB_ID=%s\n' "$TENANCY" "$COMP" "$ADB" > "$IDS"
    echo "Ids gravados em $IDS." ;;

  estado)
    carregar_ids
    oci_ db autonomous-database get --autonomous-database-id "$ADB_ID" \
      --query 'data.{nome:"display-name", banco:"db-name", estado:"lifecycle-state", versao:"db-version", gratuito:"is-free-tier", mtls:"is-mtls-connection-required", workload:"db-workload"}' \
      --output table ;;

  ligar)
    carregar_ids
    EST=$(oci_ db autonomous-database get --autonomous-database-id "$ADB_ID" --query 'data."lifecycle-state"' --raw-output)
    if [[ "$EST" == "AVAILABLE" ]]; then echo "O banco já está AVAILABLE."; exit 0; fi
    oci_ db autonomous-database start --autonomous-database-id "$ADB_ID" \
      --wait-for-state AVAILABLE --max-wait-seconds 900 --query 'data."lifecycle-state"' --raw-output ;;

  desligar)
    carregar_ids
    oci_ db autonomous-database stop --autonomous-database-id "$ADB_ID" \
      --wait-for-state STOPPED --max-wait-seconds 900 --query 'data."lifecycle-state"' --raw-output ;;

  wallet)
    carregar_ids
    W="$DIR/wallet"; TMP=$(mktemp -d)
    trap 'rm -rf "$TMP"' EXIT
    PW=$(senha_wallet)
    oci_ db autonomous-database generate-wallet --autonomous-database-id "$ADB_ID" \
      --password "$PW" --file "$TMP/wallet.zip" --generate-type SINGLE >/dev/null
    rm -rf "$W"; mkdir -p "$W"; chmod 700 "$W"
    python3 - "$TMP/wallet.zip" "$W" <<'PY'
import sys, zipfile, os
z = zipfile.ZipFile(sys.argv[1])
for n in ("tnsnames.ora", "ewallet.pem", "sqlnet.ora"):
    if n in z.namelist():
        dst = os.path.join(sys.argv[2], n)
        with open(dst, "wb") as f: f.write(z.read(n))
        os.chmod(dst, 0o600)
PY
    echo "Wallet em $W (tnsnames.ora, ewallet.pem). Serviços disponíveis:"
    grep -oE '^[a-z0-9_]+_(high|medium|low|tp|tpurgent)' "$W/tnsnames.ora" | sed 's/^/  /' ;;

  rotacionar)
    carregar_ids
    read -r -p "Isto invalida TODAS as wallets já baixadas (inclusive a do Render). Continuar? [s/N] " r
    [[ "$r" == "s" ]] || exit 0
    oci_ db autonomous-database-wallet update --autonomous-database-id "$ADB_ID" --should-rotate true >/dev/null
    echo "Wallet rotacionada. Rode '$0 wallet' e atualize os Secret Files do Render." ;;

  *)
    sed -n '2,15p' "$0" ;;
esac
