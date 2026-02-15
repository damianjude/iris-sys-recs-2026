import os
import logging
from datetime import datetime, timedelta
import time
import subprocess
import hashlib
from pathlib import Path
import tarfile

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("backup")

BACKUP_INTERVAL = int(os.getenv("BACKUP_INTERVAL", 3600))
BACKUP_DIR = os.getenv("BACKUP_DIR", "/backups")
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", 30))
CODE_SOURCE_DIR = os.getenv("CODE_SOURCE_DIR", "/code")

MYSQL_HOST = os.getenv("MYSQL_HOST", "db")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USERNAME = os.getenv("MYSQL_USERNAME", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "rails_password")

INCLUDE_DIRS = sorted(["app", "config", "db", "grafana", "mysqld-exporter",
                        "nginx", "prometheus", "public", "test"])


def file_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def comparedb(db_dir, tmp_file):
    tmp_sha = file_hash(tmp_file)
    for name in os.listdir(db_dir):
        if name.startswith("backup_") and name.endswith(".sql"):
            backup_path = os.path.join(db_dir, name)
            if os.path.isfile(backup_path) and file_hash(backup_path) == tmp_sha:
                return True
    return False


def compute_code_hash(base_dir):
    h = hashlib.sha256()
    for directory in INCLUDE_DIRS:
        dir_path = base_dir / directory
        if not dir_path.exists():
            continue
        for item in sorted(dir_path.rglob("*")):
            if item.is_file():
                rel = str(item.relative_to(base_dir))
                h.update(rel.encode())
                h.update(file_hash(item).encode())
    return h.hexdigest()


def compare_code(code_dir, current_hash):
    hash_file = os.path.join(code_dir, ".last_code_hash")
    if os.path.isfile(hash_file):
        with open(hash_file, "r") as f:
            return f.read().strip() == current_hash
    return False


def save_code_hash(code_dir, current_hash):
    hash_file = os.path.join(code_dir, ".last_code_hash")
    with open(hash_file, "w") as f:
        f.write(current_hash)


def cleanup_old_backups(backup_dir, retention_days):
    cutoff = datetime.now() - timedelta(days=retention_days)
    removed = 0
    for subdir in ("db", "code"):
        target = os.path.join(backup_dir, subdir)
        if not os.path.isdir(target):
            continue
        for name in os.listdir(target):
            if name.startswith("."):
                continue
            filepath = os.path.join(target, name)
            if not os.path.isfile(filepath):
                continue
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            if mtime < cutoff:
                os.remove(filepath)
                logger.info("Deleted old backup: %s", filepath)
                removed += 1
    if removed:
        logger.info("Rotation removed %d old backup(s).", removed)


while True:
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        db_dir = os.path.join(BACKUP_DIR, "db")
        code_dir = os.path.join(BACKUP_DIR, "code")
        os.makedirs(db_dir, exist_ok=True)
        os.makedirs(code_dir, exist_ok=True)

        tmp_file = os.path.join(db_dir, f".tmp_backup_{timestamp}.sql")
        backup_file = os.path.join(db_dir, f"backup_{timestamp}.sql")

        with open(tmp_file, "wb") as outf:
            subprocess.run(
                ["mysqldump", f"-h{MYSQL_HOST}", f"-P{MYSQL_PORT}",
                 f"-u{MYSQL_USERNAME}", f"-p{MYSQL_PASSWORD}",
                 "--all-databases", "--ssl=FALSE"],
                stdout=outf, check=True,
            )

        if not comparedb(db_dir, tmp_file):
            os.rename(tmp_file, backup_file)
            logger.info("DB Backup created at %s", backup_file)
        else:
            logger.info("DB Backup unchanged. Skipping.")
            os.remove(tmp_file)

        base_dir = Path(CODE_SOURCE_DIR)
        current_hash = compute_code_hash(base_dir)

        if not compare_code(code_dir, current_hash):
            code_backup_file = os.path.join(code_dir, f"backup_{timestamp}.tar.xz")
            with tarfile.open(code_backup_file, "w:xz") as tar:
                for directory in INCLUDE_DIRS:
                    dir_path = base_dir / directory
                    if not dir_path.exists():
                        continue
                    for item in dir_path.rglob("*"):
                        tar.add(item, arcname=item.relative_to(base_dir))
            save_code_hash(code_dir, current_hash)
            logger.info("Code Backup created at %s", code_backup_file)
        else:
            logger.info("Code Backup unchanged. Skipping.")


        cleanup_old_backups(BACKUP_DIR, RETENTION_DAYS)

    except Exception:
        logger.exception("Backup cycle failed. Will retry next interval.")

    time.sleep(BACKUP_INTERVAL)