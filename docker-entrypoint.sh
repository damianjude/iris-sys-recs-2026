#!/bin/sh
set -e

# Read RAILS_MASTER_KEY from Docker secret
if [ -f /run/secrets/rails_master_key ]; then
  export RAILS_MASTER_KEY=$(cat /run/secrets/rails_master_key)
else
  echo "ERROR: /run/secrets/rails_master_key not found" >&2
  exit 1
fi

# Clean up stale PID files
rm -f tmp/pids/server.pid

# Exec replaces this shell with the CMD process (PID 1)
exec "$@"
