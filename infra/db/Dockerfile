# Official postgres image (Netcompany rule: vendor images only) + pgvector from the PostgreSQL apt repo.
FROM postgres:16@sha256:3950ad7c3148ca2175ef1b6c36c9efbf78957ae8fbe8b3a5d7c35af50500382f
RUN apt-get update \
 && apt-get install -y --no-install-recommends postgresql-16-pgvector \
 && rm -rf /var/lib/apt/lists/*
COPY init.sql /docker-entrypoint-initdb.d/01-init.sql
COPY 02-litellm.sql /docker-entrypoint-initdb.d/02-litellm.sql
COPY 03-doc-chunk-lang.sql /docker-entrypoint-initdb.d/03-doc-chunk-lang.sql
COPY 04-trace-shadow.sql /docker-entrypoint-initdb.d/04-trace-shadow.sql
COPY 05-honeytokens.sql /docker-entrypoint-initdb.d/05-honeytokens.sql
COPY 06-breakit.sql /docker-entrypoint-initdb.d/06-breakit.sql
COPY 06-extension.sql /docker-entrypoint-initdb.d/06-extension.sql
COPY 06-tool-requests.sql /docker-entrypoint-initdb.d/06-tool-requests.sql
COPY 07-analyst-login.sql /docker-entrypoint-initdb.d/07-analyst-login.sql
