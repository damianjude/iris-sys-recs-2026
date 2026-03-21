import os
import logging
from datetime import datetime
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
RETENTION_COUNT = int(os.getenv("RETENTION_COUNT", 5))
CODE_SOURCE_DIR = os.getenv("CODE_SOURCE_DIR", "/code")
NFS_SOURCE_DIR = os.getenv("NFS_SOURCE_DIR", "/nfs")

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


def list_backup_files(backup_dir, expected_suffix):
    files = []
    for name in os.listdir(backup_dir):
        if not (name.startswith("backup_") and name.endswith(expected_suffix)):
            continue
        path = os.path.join(backup_dir, name)
        if os.path.isfile(path):
            files.append(path)
    return files


def compare_backup_file(backup_dir, tmp_file, suffix):
    tmp_sha = file_hash(tmp_file)
    for backup_path in list_backup_files(backup_dir, suffix):
        if file_hash(backup_path) == tmp_sha:
            return True
    return False


def add_directory_contents_to_tar(tar, source_dir, arcname_prefix):
    source_path = Path(source_dir)
    if not source_path.exists() or not source_path.is_dir():
        return

    for item in sorted(source_path.rglob("*")):
        relative_item = item.relative_to(source_path)
        tar.add(item, arcname=Path(arcname_prefix) / relative_item)


def cleanup_old_backups(backup_dir, retention_count):
    keep = max(1, retention_count)
    removed = 0
    suffixes = {
        "db": ".sql",
        "code": ".tar.xz",
        "nfs": ".tar.xz",
    }
    for subdir, suffix in suffixes.items():
        target = os.path.join(backup_dir, subdir)
        if not os.path.isdir(target):
            continue
        backup_files = list_backup_files(target, suffix)

        backup_files.sort(key=os.path.getmtime, reverse=True)
        for filepath in backup_files[keep:]:
            os.remove(filepath)
            logger.info("Deleted old backup: %s", filepath)
            removed += 1
    if removed:
        logger.info("Rotation removed %d old backup(s); kept latest %d per category.", removed, keep)


def archive_nfs_storage(source_dir, backup_dir, timestamp):
    source_path = Path(source_dir)
    if not source_path.exists():
        logger.warning("NFS source dir %s does not exist. Skipping NFS backup.", source_dir)
        return

    if not source_path.is_dir():
        logger.warning("NFS source path %s is not a directory. Skipping NFS backup.", source_dir)
        return

    tmp_archive = os.path.join(backup_dir, f".tmp_backup_{timestamp}.tar.xz")
    backup_archive = os.path.join(backup_dir, f"backup_{timestamp}.tar.xz")

    with tarfile.open(tmp_archive, "w:xz") as tar:
        add_directory_contents_to_tar(tar, source_path, "shared_storage")

    if not compare_backup_file(backup_dir, tmp_archive, ".tar.xz"):
        os.rename(tmp_archive, backup_archive)
        logger.info("NFS Backup created at %s", backup_archive)
    else:
        logger.info("NFS Backup unchanged. Skipping.")
        os.remove(tmp_archive)


while True:
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        db_dir = os.path.join(BACKUP_DIR, "db")
        code_dir = os.path.join(BACKUP_DIR, "code")
        nfs_dir = os.path.join(BACKUP_DIR, "nfs")
        os.makedirs(db_dir, exist_ok=True)
        os.makedirs(code_dir, exist_ok=True)
        os.makedirs(nfs_dir, exist_ok=True)

        tmp_file = os.path.join(db_dir, f".tmp_backup_{timestamp}.sql")
        backup_file = os.path.join(db_dir, f"backup_{timestamp}.sql")

        with open(tmp_file, "wb") as outf:
            subprocess.run(
                ["mysqldump", f"-h{MYSQL_HOST}", f"-P{MYSQL_PORT}",
                 f"-u{MYSQL_USERNAME}", f"-p{MYSQL_PASSWORD}",
                 "--all-databases", "--ssl=FALSE"],
                stdout=outf, check=True,
            )

        if not compare_backup_file(db_dir, tmp_file, ".sql"):
            os.rename(tmp_file, backup_file)
            logger.info("DB Backup created at %s", backup_file)
        else:
            logger.info("DB Backup unchanged. Skipping.")
            os.remove(tmp_file)

        base_dir = Path(CODE_SOURCE_DIR)
        tmp_code_file = os.path.join(code_dir, f".tmp_backup_{timestamp}.tar.xz")
        code_backup_file = os.path.join(code_dir, f"backup_{timestamp}.tar.xz")

        with tarfile.open(tmp_code_file, "w:xz") as tar:
            for directory in INCLUDE_DIRS:
                dir_path = base_dir / directory
                if not dir_path.exists():
                    continue
                add_directory_contents_to_tar(tar, dir_path, directory)

        if not compare_backup_file(code_dir, tmp_code_file, ".tar.xz"):
            os.rename(tmp_code_file, code_backup_file)
            logger.info("Code Backup created at %s", code_backup_file)
        else:
            logger.info("Code Backup unchanged. Skipping.")
            os.remove(tmp_code_file)

        archive_nfs_storage(NFS_SOURCE_DIR, nfs_dir, timestamp)


        cleanup_old_backups(BACKUP_DIR, RETENTION_COUNT)

    except Exception:
        logger.exception("Backup cycle failed. Will retry next interval.")

    time.sleep(BACKUP_INTERVAL)