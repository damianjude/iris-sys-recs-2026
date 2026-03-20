#!/bin/sh
set -e

# Mount shared NFS storage inside the container if ENABLE_ENTRYPOINT_NFS_MOUNT is set to 1 to avoid NFS race condition
if [ "${ENABLE_ENTRYPOINT_NFS_MOUNT:-1}" = "1" ]; then
  NFS_SERVER="${NFS_SERVER:-nfs}"
  NFS_EXPORT_PATH="${NFS_EXPORT_PATH:-/}"
  NFS_MOUNT_PATH="${NFS_MOUNT_PATH:-/app/storage}"
  NFS_MOUNT_OPTS="${NFS_MOUNT_OPTS:-rw,nfsvers=4,soft,timeo=180,tcp}"
  NFS_WAIT_RETRIES="${NFS_WAIT_RETRIES:-60}"
  NFS_WAIT_SECONDS="${NFS_WAIT_SECONDS:-2}"

  mkdir -p "$NFS_MOUNT_PATH"

  if ! mountpoint -q "$NFS_MOUNT_PATH"; then
    retry=0
    until mount -t nfs -o "$NFS_MOUNT_OPTS" "${NFS_SERVER}:${NFS_EXPORT_PATH}" "$NFS_MOUNT_PATH"; do
      retry=$((retry + 1))
      if [ "$retry" -ge "$NFS_WAIT_RETRIES" ]; then
        echo "ERROR: failed to mount NFS ${NFS_SERVER}:${NFS_EXPORT_PATH} at ${NFS_MOUNT_PATH}" >&2
        exit 1
      fi
      sleep "$NFS_WAIT_SECONDS"
    done
  fi
fi

# Read RAILS_MASTER_KEY from Docker secret
if [ -f /run/secrets/rails_master_key ]; then
  export RAILS_MASTER_KEY=$(cat /run/secrets/rails_master_key)
else
  echo "ERROR: /run/secrets/rails_master_key not found" >&2
  exit 1
fi

# Clean up stale PID files
rm -f tmp/pids/server.pid

chown -R rails:rails /app/tmp /app/log /app/storage

# Run app as non-root and PID 1 after NFS mount and setup
exec gosu rails "$@"
