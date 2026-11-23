-- Apaga as tabelas do Respira no schema em que for executado (CASCADE CONSTRAINTS
-- resolve as FKs; PURGE não deixa nada na lixeira). Na próxima subida, o backend
-- recria o esquema a partir dos modelos (bootstrap do M2).
-- DESTRUTIVO: rodar só com confirmação explícita do André.
--   uv run --with oracledb python ops/oracle/respira_sql.py rodar ops/oracle/apagar_tabelas_app.sql --como app
BEGIN
  FOR t IN (
    SELECT table_name FROM user_tables
     WHERE table_name IN ('ACOMPANHAMENTO','ALEMBIC_VERSION','COLETA_RECURSO','CONSENTIMENTO','CONTA',
                          'DIVIDA','EVENTO','FATURA','INSTITUICAO','LICAO','PLANO','PLANO_ITEM',
                          'RENDA_DETECTADA','SESSAO','TRANSACAO','USUARIO','WEBHOOK_LOG')
  ) LOOP
    EXECUTE IMMEDIATE 'DROP TABLE "' || t.table_name || '" CASCADE CONSTRAINTS PURGE';
  END LOOP;
END;
/
