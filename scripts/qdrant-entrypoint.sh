#!/bin/sh
set -eu
if [ -n "${OPENCMO_QDRANT_API_KEY:-}" ]; then
  export QDRANT__SERVICE__API_KEY="$OPENCMO_QDRANT_API_KEY"
fi
exec /qdrant/entrypoint.sh "$@"
