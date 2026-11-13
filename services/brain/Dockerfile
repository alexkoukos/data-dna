# Brain service. Multi-stage, CPU only, no PyTorch.
FROM python:3.12-slim AS base
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
HEALTHCHECK --interval=10s --timeout=3s --retries=12 CMD python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://localhost:8001/healthz').status==200 else 1)"
CMD ["uvicorn", "brain.main:app", "--host", "0.0.0.0", "--port", "8001"]
