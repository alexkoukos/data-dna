#!/bin/sh
# Create secrets/hmac_key (the HMAC key for the split store) if it does not exist yet.
# 32 random bytes from the OS CSPRNG, hex encoded. Never commit it; never put it in a vault.
# Use --force to replace it (existing split values then fail their integrity check).
set -eu
dir="$(cd "$(dirname "$0")/.." && pwd)/secrets"
file="$dir/hmac_key"
mkdir -p "$dir"
# Docker creates an empty directory here when the file is missing at `compose up`. Replace it.
if [ -d "$file" ]; then
  rmdir "$file" 2>/dev/null || {
    echo "secrets/hmac_key is a directory that Docker created; remove it first:" >&2
    echo "  sudo rmdir secrets/hmac_key && sh scripts/gen_hmac_key.sh" >&2
    exit 1
  }
fi
if [ -s "$file" ] && [ "${1:-}" != "--force" ]; then
  echo "secrets/hmac_key already exists (use --force to replace it)"
  exit 0
fi
umask 077
head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n' > "$file"
chmod 644 "$file"   # the container user must be able to read the mounted secret
echo "wrote secrets/hmac_key"
