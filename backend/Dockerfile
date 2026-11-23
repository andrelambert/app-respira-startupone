# Backend do Respira (FastAPI) — imagem para o Render e para o docker compose local.
# Nenhum segredo entra na imagem: .env e wallet ficam de fora (.dockerignore) e
# chegam em tempo de execução (variáveis de ambiente e Secret Files do Render).
# Mesma versão do backend/.python-version (a usada no desenvolvimento e nos testes).
FROM python:3.13-slim

# uv numa versão fixa, copiado da imagem oficial.
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependências primeiro (camada em cache enquanto o uv.lock não muda).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev

# Usuário sem privilégios.
RUN useradd --create-home --uid 10001 respira && chown -R respira /app
USER respira

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

# --proxy-headers: atrás do proxy do Render/Vercel, o IP real do visitante é o
# que vale para os limites de tentativa.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
