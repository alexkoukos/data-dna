-- The free-text analyst role (infra/db/init.sql) becomes a login role with hard limits. It has no
-- password here: the brain sets a random one in memory at each start, so none is stored anywhere.
ALTER ROLE analyst_ro WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 3;
ALTER ROLE analyst_ro SET statement_timeout = '3s';
ALTER ROLE analyst_ro SET default_transaction_read_only = on;
