# Vendor image pinned to a stable release (Netcompany rule: vendor images only).
FROM ghcr.io/berriai/litellm:v1.109.1
WORKDIR /app
COPY config.yaml dna_guardrail.py dna_inspect.py /app/
EXPOSE 4000
HEALTHCHECK --interval=10s --timeout=5s --retries=12 --start-period=30s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:4000/health/liveliness')" || exit 1
CMD ["--config", "/app/config.yaml", "--port", "4000"]
