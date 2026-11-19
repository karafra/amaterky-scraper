FROM ghcr.io/astral-sh/uv:0.13.7 AS uv
FROM python:3.12-slim

RUN mkdir -p /data /app \
    && chown 101:101 /data
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY scraper /app/scraper
USER 101:101

CMD ["/app/.venv/bin/python", "-m", "scraper"]
