# Brain service. Multi-stage, CPU only, no PyTorch.
FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv
WORKDIR /app

FROM base AS deps
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM deps AS runtime
COPY src ./src
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH" HF_HOME=/opt/models/hf EMBED_THREADS=4
# Bake the embedding model (about 120 MB) into the image so the first start needs no internet.
RUN python -c "from brain.documents.embeddings import fetch_model_files; fetch_model_files()"
ENV HF_HUB_OFFLINE=1
EXPOSE 8001
# start-period: model and NLP loading can take over a minute on a slow machine; failures in that
# window do not count, so a slow first start is not marked unhealthy.
HEALTHCHECK --interval=10s --timeout=3s --retries=12 --start-period=120s CMD python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://localhost:8001/healthz').status==200 else 1)"
CMD ["uvicorn", "brain.main:app", "--host", "0.0.0.0", "--port", "8001"]

# Test image: the runtime plus dev dependencies and tests (compose service `splitstore-tests`).
FROM runtime AS test
RUN uv sync --frozen
COPY tests ./tests

# Keep the runtime image the default (last) target. Runs as an unprivileged user. The code, the
# venv and the baked model stay root-owned and read-only; only the volume mount points are owned by
# the app user (a new named volume copies this ownership on first use).
FROM runtime AS app
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin app \
 && mkdir -p /models /var/dna/logs /var/dna/keys /var/dna/breakit \
 && chown app:app /models /var/dna/logs /var/dna/keys /var/dna/breakit
USER app
