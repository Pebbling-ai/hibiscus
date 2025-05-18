FROM python:3.12-slim AS base

FROM base AS builder
COPY --from=ghcr.io/astral-sh/uv:0.4.9 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

COPY uv.lock pyproject.toml /app/

RUN --mount=type=cache,id=s/$RAILWAY_SERVICE_ID-uv-cache,target=/root/.cache/uv \
  uv sync --frozen --no-install-project --no-dev
COPY . /app
RUN --mount=type=cache,id=s/$RAILWAY_SERVICE_ID-uv-cache,target=/root/.cache/uv \
  uv sync --frozen --no-dev

FROM base
WORKDIR /app
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH"

# Create non-root user with explicit UID/GID
RUN groupadd -g 1001 appgroup && \
    useradd -m -u 1001 -g appgroup -s /bin/bash appuser && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

# Use the full module path to ensure the app can be found
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]