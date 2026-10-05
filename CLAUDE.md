# Respira — instruções para o Claude Code

O contexto completo do produto (regras de negócio, integração Belvo, copy,
segurança) está em `docs/contexto-produto.md`. As referências `§N` no código
apontam para as seções dele. O `README.md` é para humanos (professor, quem
clonar o repo) — mantenha-o atualizado quando mudar stack, como rodar ou limitações.

@docs/contexto-produto.md

## Rodar

- Backend: `cd backend && uv run uvicorn app.main:app --reload --port 8000`
- Frontend: `cd frontend && npm run dev` → http://localhost:5173
- Testes: `cd backend && uv run pytest` · `cd frontend && npm test`

## Contas

- Provedor é POR USUÁRIO: conta `demo` (Juliana) → `FixtureProvider`; conta registrada → Belvo real
  (`app/services/contexto.py`). Login por cookie HttpOnly + sessão no banco (`app/services/auth.py`).
- Credenciais da Belvo e da demo ficam só em `backend/.env` (gitignored). Nunca no código ou no chat.

## Onde mora cada coisa

- Motor de plano (§5): `backend/app/domain/planner.py` — Python puro, testado contra a §14.1.
- Belvo → domínio (§7.7): `backend/app/providers/mapping.py` — único lugar que conhece os nomes da Belvo.
- PFM (contas, faturas, extrato paginado): `backend/app/routers/pfm.py` + `app/repositories/pfm.py`;
  telas em `frontend/src/routes/contas/`. Fatura de cartão sem rotativo = taxa 0 e "mínimo" = total.
- Nome e logo de banco: catálogo da Belvo (`GET /api/institutions/?country_code__in=BR&type=bank`) gravado na
  tabela `instituicao` (`app/services/instituicoes.py`), atualizado na subida a cada 7 dias. Nunca exibir o
  código cru (`ofnubank_br_retail`); no frontend, use `<LogoBanco>`.
- SQL só em `backend/app/repositories/` (§6.4).
- Strings da interface: `frontend/src/lib/copy.ts` (§11). Dinheiro: `frontend/src/lib/money.ts` (centavos inteiros).
