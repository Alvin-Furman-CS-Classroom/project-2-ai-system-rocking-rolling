# Stage 1: Build the presentation frontend
FROM node:22-alpine AS frontend-builder
WORKDIR /app
RUN corepack enable

COPY presentation/package.json presentation/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY presentation/ ./
RUN pnpm build

# Stage 2: Python runtime with Flask
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY modules/ ./modules/
RUN uv sync --frozen --no-dev --all-packages

COPY --from=frontend-builder /app/dist ./presentation/dist

ENV STATIC_DIR=/app/presentation/dist
ENV PYTHONPATH=modules/api/src
EXPOSE 5000

CMD ["uv", "run", "--no-dev", "gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--worker-class", "gevent", "api.app:app"]
