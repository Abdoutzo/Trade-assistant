# One image: the website is built with Node, then served by the Python API.

FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PATH="/app/.venv/bin:$PATH" ENV=prod
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --extra postgres --no-install-project
COPY trade_assistant ./trade_assistant
RUN uv sync --frozen --no-dev --extra postgres
COPY --from=web /web/dist ./web/dist
RUN useradd --create-home app && mkdir -p data && chown app data
USER app
EXPOSE 8000
# The host (Render) gives the port in $PORT and sits behind a proxy: trust its X-Forwarded-* headers.
CMD uvicorn trade_assistant.api:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips="*"
