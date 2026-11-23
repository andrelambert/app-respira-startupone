--------------------------------------------------------------------------------
-- Respira — motor de plano de quitação em PL/SQL, sobre as tabelas deste app
-- (M3, Fase 7: "dupla execução").
--
-- É o PKG_PLANO da Fase 5 (referência: 04_motor_plano.sql) adaptado ao esquema
-- da aplicação: tabela DIVIDA (singular), colunas SALDO_DEVEDOR, TAXA_JUROS_MES,
-- PARCELA_MINIMA. Roda dentro do Oracle; o backend compara o resultado com o
-- planner.py (Python) e só mostra o selo "Conferido no Oracle" se coincidir ao
-- centavo.
--
-- Mesmas regras do planner.py (docs/contexto-produto.md §5.3):
--   - juros arredondados a 2 casas a cada incidência, ANTES do pagamento;
--   - mínimos na ordem da estratégia, depois a sobra inteira para a dívida da vez;
--   - "primeira quitação" só conta a feita com a sobra (passo 2), como na Fase 5;
--   - encerra com todas as dívidas <= 0,01, aos 600 meses, ou se o saldo total
--     passar de 1000x o inicial (trava de divergência, igual ao Python);
--   - desempates: AVALANCHE taxa DESC, saldo ASC; SNOWBALL saldo ASC, taxa DESC;
--     EQUILIBRADO menor dívida primeiro e o resto como o AVALANCHE. Último
--     desempate pelo id como texto — o mesmo critério do Python (ids são str lá).
--
-- Idempotente (CREATE OR REPLACE): o backend instala a cada subida no Oracle.
-- Instalação manual: respira_sql.py rodar backend/oracle/pkg_plano_app.sql --como app
--------------------------------------------------------------------------------

CREATE OR REPLACE PACKAGE pkg_plano_app AS

  -- Simula uma estratégia para o usuário com a capacidade dada.
  -- p_metodo: AVALANCHE | SNOWBALL | EQUILIBRADO.
  -- Devolve JSON: {"meses": n, "juros": n.nn, "primeira": n|null, "converge": true|false}
  FUNCTION simular (p_usuario_id IN NUMBER,
                    p_metodo     IN VARCHAR2,
                    p_capacidade IN NUMBER) RETURN VARCHAR2;

END pkg_plano_app;
/

CREATE OR REPLACE PACKAGE BODY pkg_plano_app AS

  c_max_meses   CONSTANT PLS_INTEGER := 600;
  c_residual    CONSTANT NUMBER := 0.01;
  c_divergencia CONSTANT NUMBER := 1000;

  TYPE r_divida IS RECORD (saldo NUMBER, taxa NUMBER, minima NUMBER);
  TYPE t_dividas IS TABLE OF r_divida INDEX BY PLS_INTEGER;

  ----------------------------------------------------------------------------
  PROCEDURE carregar (p_usuario_id IN NUMBER, p_metodo IN VARCHAR2, p_lista OUT t_dividas) IS
    i PLS_INTEGER := 0;
  BEGIN
    FOR r IN (
      WITH abertas AS (
        SELECT id, ROUND(saldo_devedor, 2) AS saldo, taxa_juros_mes AS taxa, parcela_minima AS minima,
               ROW_NUMBER() OVER (ORDER BY saldo_devedor ASC, taxa_juros_mes DESC, TO_CHAR(id)) AS pos_menor
          FROM divida
         WHERE usuario_id = p_usuario_id
           AND saldo_devedor > 0
      )
      SELECT saldo, taxa, minima
        FROM abertas
       ORDER BY
         CASE WHEN p_metodo = 'EQUILIBRADO' AND pos_menor = 1 THEN 0 ELSE 1 END,
         CASE WHEN p_metodo = 'SNOWBALL' THEN saldo END ASC,
         CASE WHEN p_metodo = 'SNOWBALL' THEN NULL ELSE taxa END DESC,
         CASE WHEN p_metodo = 'SNOWBALL' THEN taxa END DESC,
         CASE WHEN p_metodo = 'SNOWBALL' THEN NULL ELSE saldo END ASC,
         TO_CHAR(id))
    LOOP
      i := i + 1;
      p_lista(i).saldo  := r.saldo;
      p_lista(i).taxa   := r.taxa;
      p_lista(i).minima := r.minima;
    END LOOP;
  END carregar;

  ----------------------------------------------------------------------------
  FUNCTION simular (p_usuario_id IN NUMBER,
                    p_metodo     IN VARCHAR2,
                    p_capacidade IN NUMBER) RETURN VARCHAR2 IS
    v_d         t_dividas;
    v_cap       NUMBER := ROUND(p_capacidade, 2);
    v_mes       PLS_INTEGER := 0;
    v_juros_tot NUMBER := 0;
    v_primeira  PLS_INTEGER := NULL;
    v_sobra     NUMBER;
    v_juros     NUMBER;
    v_pgto      NUMBER;
    v_restantes PLS_INTEGER;
    v_inicial   NUMBER := 0;
    v_total     NUMBER;
    v_json      VARCHAR2(200);
    v_converge  VARCHAR2(5);
  BEGIN
    IF p_metodo NOT IN ('AVALANCHE', 'SNOWBALL', 'EQUILIBRADO') THEN
      RAISE_APPLICATION_ERROR(-20001, 'metodo invalido');
    END IF;
    carregar(p_usuario_id, p_metodo, v_d);
    IF v_d.COUNT = 0 OR v_cap <= 0 THEN
      -- Sem dívidas, o "plano" já terminou; sem capacidade, não converge (§14.2).
      v_converge := CASE WHEN v_d.COUNT = 0 THEN 'true' ELSE 'false' END;
      SELECT JSON_OBJECT('meses' VALUE 0, 'juros' VALUE 0, 'primeira' VALUE NULL,
                         'converge' VALUE v_converge FORMAT JSON NULL ON NULL)
        INTO v_json FROM dual;
      RETURN v_json;
    END IF;
    FOR i IN 1 .. v_d.COUNT LOOP
      v_inicial := v_inicial + v_d(i).saldo;
    END LOOP;

    LOOP
      v_mes   := v_mes + 1;
      v_sobra := v_cap;

      -- 1) Juros do mês e pagamento mínimo de cada dívida aberta, na ordem
      FOR i IN 1 .. v_d.COUNT LOOP
        IF v_d(i).saldo > 0 THEN
          v_juros      := ROUND(v_d(i).saldo * v_d(i).taxa, 2);
          v_d(i).saldo := v_d(i).saldo + v_juros;
          v_juros_tot  := v_juros_tot + v_juros;
          v_pgto       := LEAST(v_d(i).minima, v_d(i).saldo, v_sobra);
          v_d(i).saldo := v_d(i).saldo - v_pgto;
          v_sobra      := v_sobra - v_pgto;
        END IF;
      END LOOP;

      -- 2) A sobra vai integralmente para a dívida da vez
      FOR i IN 1 .. v_d.COUNT LOOP
        EXIT WHEN v_sobra <= 0;
        IF v_d(i).saldo > 0 THEN
          v_pgto       := LEAST(v_sobra, v_d(i).saldo);
          v_d(i).saldo := v_d(i).saldo - v_pgto;
          v_sobra      := v_sobra - v_pgto;
          IF v_d(i).saldo <= 0 AND v_primeira IS NULL THEN
            v_primeira := v_mes;
          END IF;
        END IF;
      END LOOP;

      -- 3) Encerrou?
      v_restantes := 0;
      v_total     := 0;
      FOR i IN 1 .. v_d.COUNT LOOP
        IF v_d(i).saldo > c_residual THEN v_restantes := v_restantes + 1; END IF;
        IF v_d(i).saldo > 0 THEN v_total := v_total + v_d(i).saldo; END IF;
      END LOOP;
      EXIT WHEN v_restantes = 0 OR v_mes >= c_max_meses;
      EXIT WHEN v_total > v_inicial * c_divergencia;
    END LOOP;

    v_converge := CASE WHEN v_restantes = 0 THEN 'true' ELSE 'false' END;
    SELECT JSON_OBJECT('meses' VALUE v_mes,
                       'juros' VALUE ROUND(v_juros_tot, 2),
                       'primeira' VALUE v_primeira,
                       'converge' VALUE v_converge FORMAT JSON
                       NULL ON NULL)
      INTO v_json FROM dual;
    RETURN v_json;
  END simular;

END pkg_plano_app;
/
