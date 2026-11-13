# Official postgres image (Netcompany rule: vendor images only) + pgvector from the PostgreSQL apt repo.
FROM postgres:16
RUN apt-get update \
 && apt-get install -y --no-install-recommends postgresql-16-pgvector \
 && rm -rf /var/lib/apt/lists/*
COPY init.sql /docker-entrypoint-initdb.d/01-init.sql
