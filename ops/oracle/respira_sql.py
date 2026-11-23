"""Operações SQL do Respira no Oracle Autonomous AI Database, sem expor senhas.

Lê as senhas de ~/.oracle/respira/segredos.env e a wallet de ~/.oracle/respira/wallet.
Rodar com o driver python-oracledb (modo thin, sem Instant Client):

    uv run --with oracledb python respira_sql.py verificar            # conecta como ADMIN e mostra versão
    uv run --with oracledb python respira_sql.py criar-usuarios       # cria/atualiza RESPIRA_APP e RESPIRA_TESTE
    uv run --with oracledb python respira_sql.py tabelas [--como app] # lista as tabelas do schema
    uv run --with oracledb python respira_sql.py rodar ARQ.sql --como app   # executa um script (PL/SQL com "/")
    uv run --with oracledb python respira_sql.py contar               # linhas das tabelas principais do app

Opções: --dsn <alias> (padrão: o primeiro *_tp do tnsnames.ora).
Nunca imprime senhas, usuários de terceiros ou dados de usuários — só nomes de objetos e contagens.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import oracledb

DIR = Path.home() / ".oracle" / "respira"
WALLET = DIR / "wallet"
SEGREDOS = DIR / "segredos.env"

USUARIOS = {"app": "RESPIRA_APP", "teste": "RESPIRA_TESTE", "admin": "ADMIN"}
CHAVE_SENHA = {"app": "RESPIRA_APP_PASSWORD", "teste": "RESPIRA_TESTE_PASSWORD", "admin": "ADB_ADMIN_PASSWORD"}
COTA = {"RESPIRA_APP": "2G", "RESPIRA_TESTE": "500M"}
PRIVILEGIOS = "CREATE SESSION, CREATE TABLE, CREATE SEQUENCE, CREATE VIEW, CREATE PROCEDURE, CREATE TYPE"
SENHA_VALIDA = re.compile(r"^[A-Za-z0-9#_]{12,30}$")


def segredos() -> dict[str, str]:
    if not SEGREDOS.exists():
        sys.exit(f"Falta {SEGREDOS}. Rode gerar_segredos.sh primeiro.")
    out = {}
    for linha in SEGREDOS.read_text().splitlines():
        if "=" in linha and not linha.lstrip().startswith("#"):
            k, v = linha.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def dsn_padrao() -> str:
    tns = WALLET / "tnsnames.ora"
    if not tns.exists():
        sys.exit(f"Falta {tns}. Rode: bash respira_oci.sh wallet")
    aliases = re.findall(r"^([a-z0-9_]+_tp)\s*=", tns.read_text(), flags=re.M)
    if not aliases:
        sys.exit("Nenhum alias *_tp no tnsnames.ora.")
    return aliases[0]


def conectar(como: str, dsn: str) -> oracledb.Connection:
    s = segredos()
    return oracledb.connect(
        user=USUARIOS[como],
        password=s[CHAVE_SENHA[como]],
        dsn=dsn,
        config_dir=str(WALLET),
        wallet_location=str(WALLET),
        wallet_password=s["ORACLE_WALLET_PASSWORD"],
    )


def verificar(dsn: str) -> None:
    with conectar("admin", dsn) as c, c.cursor() as cur:
        cur.execute("select version_full from product_component_version where rownum = 1")
        versao = cur.fetchone()[0]
        cur.execute("select sys_context('USERENV','DB_NAME') from dual")
        nome = cur.fetchone()[0]
    print(f"Conectado como ADMIN · banco {nome} · versão {versao} · serviço {dsn}")


def criar_usuarios(dsn: str) -> None:
    s = segredos()
    with conectar("admin", dsn) as c, c.cursor() as cur:
        for chave in ("app", "teste"):
            usuario, senha = USUARIOS[chave], s[CHAVE_SENHA[chave]]
            if not SENHA_VALIDA.match(senha):
                sys.exit(f"Senha de {usuario} fora do padrão esperado (12–30, letras/números).")
            cur.execute("select count(*) from dba_users where username = :u", u=usuario)
            existe = cur.fetchone()[0] > 0
            # Senha validada acima (sem aspas): pode ir entre aspas duplas no DDL.
            if existe:
                cur.execute(f'alter user {usuario} identified by "{senha}" account unlock')
                acao = "senha atualizada"
            else:
                cur.execute(f'create user {usuario} identified by "{senha}"')
                acao = "criado"
            cur.execute(f"grant {PRIVILEGIOS} to {usuario}")
            cur.execute(f"alter user {usuario} quota {COTA[usuario]} on data")
            print(f"{usuario}: {acao}; privilégios mínimos e cota {COTA[usuario]} aplicados.")


def tabelas(como: str, dsn: str) -> None:
    with conectar(como, dsn) as c, c.cursor() as cur:
        cur.execute("select table_name from user_tables order by table_name")
        nomes = [r[0] for r in cur]
    print(f"{USUARIOS[como]}: {len(nomes)} tabelas")
    for n in nomes:
        print("  " + n)


def contar(dsn: str) -> None:
    with conectar("app", dsn) as c, c.cursor() as cur:
        cur.execute("select table_name from user_tables order by table_name")
        for (t,) in cur.fetchall():
            cur.execute(f'select count(*) from "{t}"')
            print(f"  {t:<24} {cur.fetchone()[0]}")


PLSQL = re.compile(r"^\s*(create\s+(or\s+replace\s+)?(editionable\s+)?(package|type|procedure|function|trigger)|begin|declare)\b", re.I)


def comandos(texto: str) -> list[str]:
    """Divide um script no estilo SQL*Plus: PL/SQL termina numa linha só com "/";
    SQL comum termina em ";" no fim da linha (o ";" é removido)."""
    out, atual = [], []
    for linha in texto.splitlines():
        if not atual and (not linha.strip() or linha.strip().startswith("--")):
            continue
        if linha.strip() == "/":
            if atual:
                out.append("\n".join(atual).strip())
            atual = []
            continue
        atual.append(linha)
        bloco = "\n".join(atual)
        if not PLSQL.match(bloco) and linha.rstrip().endswith(";"):
            out.append(bloco.rstrip().rstrip(";").strip())
            atual = []
    if "\n".join(atual).strip():
        out.append("\n".join(atual).strip().rstrip(";") if not PLSQL.match("\n".join(atual)) else "\n".join(atual).strip())
    return [c for c in out if c]


def rodar(arquivo: Path, como: str, dsn: str) -> None:
    """Executa um script SQL/PLSQL (PL/SQL termina com uma linha contendo só "/")."""
    cmds = comandos(arquivo.read_text())
    with conectar(como, dsn) as c, c.cursor() as cur:
        for sql in cmds:
            cur.execute(sql)
        cur.execute("select name, type, line, text from user_errors order by name, sequence")
        erros = cur.fetchall()
    if erros:
        print("Objetos com erro de compilação:")
        for e in erros:
            print(f"  {e[0]} ({e[1]}) linha {e[2]}: {e[3].strip()}")
        sys.exit(1)
    print(f"{arquivo.name}: {len(cmds)} comando(s) executado(s) como {USUARIOS[como]}, sem erros de compilação.")


def main() -> None:
    p = argparse.ArgumentParser(description="SQL do Respira no Oracle (sem expor senhas)")
    p.add_argument("comando", choices=["verificar", "criar-usuarios", "tabelas", "rodar", "contar"])
    p.add_argument("arquivo", nargs="?")
    p.add_argument("--como", choices=["app", "teste", "admin"], default="app")
    p.add_argument("--dsn")
    a = p.parse_args()
    dsn = a.dsn or dsn_padrao()
    if a.comando == "verificar":
        verificar(dsn)
    elif a.comando == "criar-usuarios":
        criar_usuarios(dsn)
    elif a.comando == "tabelas":
        tabelas(a.como, dsn)
    elif a.comando == "contar":
        contar(dsn)
    else:
        if not a.arquivo:
            sys.exit("Informe o arquivo .sql")
        rodar(Path(a.arquivo), a.como, dsn)


if __name__ == "__main__":
    main()
