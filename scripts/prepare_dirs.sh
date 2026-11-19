#!/bin/sh
# Prepare host folders before `docker compose up`. The HMAC key for the split store is no longer
# made here: the brain generates it once into its app-only `keys` volume on first start.
set -eu
root="$(cd "$(dirname "$0")/.." && pwd)"
# X28 + S3: the brain runs as a non-root user (uid 10001) and approves break-it rows by writing to
# data/eval, so that folder and its CSV files must be writable by it.
if [ -d "$root/data/eval" ]; then
  chmod a+rwx "$root/data/eval" 2>/dev/null || true
  chmod a+rw "$root"/data/eval/*.csv 2>/dev/null || true
fi
