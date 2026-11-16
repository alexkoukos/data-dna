# Official postgres image (Netcompany rule: vendor images only) + pgvector from the PostgreSQL apt repo.
FROM postgres:16
RUN apt-get update \
 && apt-get install -y --no-install-recommends postgresql-16-pgvector \
 && rm -rf /var/lib/apt/lists/*
COPY init.sql /docker-entrypoint-initdb.d/01-init.sql
COPY 02-litellm.sql /docker-entrypoint-initdb.d/02-litellm.sql
COPY 03-doc-chunk-lang.sql /docker-entrypoint-initdb.d/03-doc-chunk-lang.sql
COPY 04-trace-shadow.sql /docker-entrypoint-initdb.d/04-trace-shadow.sql
COPY 05-honeytokens.sql /docker-entrypoint-initdb.d/05-honeytokens.sql
