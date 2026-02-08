import os
from datetime import datetime
import time
import subprocess
import hashlib
from pathlib import Path
import tarfile

BACKUP_INTERVAL = int(os.getenv("BACKUP_INTERVAL", 3600))
BACKUP_DIR = os.getenv("BACKUP_DIR", "/backups")

MYSQL_HOST = os.getenv("MYSQL_HOST", "db")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USERNAME = os.getenv("MYSQL_USERNAME", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "rails_password")

# Compare if two backups (DBs) are the same by comparing their SHA256 hashes
def comparedb(db_dir, tmp_file):
    for file in os.listdir(db_dir):
        if file.startswith("backup_") and file.endswith(".sql"):
            backup_path = os.path.join(db_dir, file)
            if os.path.isfile(backup_path):
                hash = hashlib.sha256()
                with open(backup_path, "rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        hash.update(chunk)
                backupsha = hash.hexdigest()
                with open(tmp_file, "rb") as f:
                    hash = hashlib.sha256()
                    for chunk in iter(lambda: f.read(65536), b""):
                        hash.update(chunk)
                tmpsha = hash.hexdigest()
                if backupsha == tmpsha:
                    return True
    return False

while True:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    db_dir = os.path.join(BACKUP_DIR, "db")
    code_dir = os.path.join(BACKUP_DIR, "code")
    os.makedirs(db_dir, exist_ok=True)
    os.makedirs(code_dir, exist_ok=True)

    # DB Backup
    tmp_file = os.path.join(db_dir, f".tmp_backup_{timestamp}.sql")
    backup_file = os.path.join(db_dir, f"backup_{timestamp}.sql")
    
    subprocess.run(["mysqldump", f"-h{MYSQL_HOST}", f"-P{MYSQL_PORT}", f"-u{MYSQL_USERNAME}", f"-p{MYSQL_PASSWORD}", "--all-databases", "--ssl=FALSE"], stdout = open(tmp_file, "wb"), check=True)
    
    # Compare the new backup with existing ones and only keep it if it's different
    if not comparedb(db_dir, tmp_file):
        os.rename(tmp_file, backup_file)
        print(f"DB Backup created at {backup_file}")
    else:
        print("DB Backup already exists. Skipping.")
        os.remove(tmp_file)
    
    # Code backup
    code_backup_file = os.path.join(code_dir, f"backup_{timestamp}.tar.xz")

    INCLUDE_DIRS = {"app", "config", "db", "grafana", "mysqld-exporter", "nginx", "prometheus", "public", "test"}

    base_dir = Path.cwd()
    with tarfile.open(os.path.join(code_backup_file), "w:xz") as tar:
        for directory in INCLUDE_DIRS:
            for item in (base_dir / directory).rglob("*"):
                if item.is_file():
                    tar.add(item, arcname=item.relative_to(base_dir))
                elif item.is_dir():
                    tar.add(item, arcname=item.relative_to(base_dir))
    print(f"Code Backup created at {code_backup_file}")

    time.sleep(BACKUP_INTERVAL)