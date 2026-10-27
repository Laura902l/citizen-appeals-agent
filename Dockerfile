FROM node:24-slim AS dashboard
WORKDIR /build
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci
COPY dashboard/ ./
RUN npm run build

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/
RUN pip install .

RUN appeal-agent generate --n 2000 --seed 42 \
    && appeal-agent train --seed 42 --min-accuracy 0.90

COPY --from=dashboard /build/dist ./dashboard/dist

RUN useradd --create-home --uid 1000 agent && chown -R agent:agent /app
USER agent

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/summary')"

ENTRYPOINT ["appeal-agent"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8000", "--today", "2026-10-05"]
