"""Database backup and restore utility.

Usage:
    py -m scripts.backup backup [path/to/backup.db]
    py -m scripts.backup restore [path/to/backup.db]
"""
from __future__ import annotations

import datetime
import os
import shutil
import sys

DB_PATH = "digital_lending.db"
BACKUP_DIR = "backups"


def backup(path: str | None = None) -> str:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    if not path:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(BACKUP_DIR, f"lendiq_backup_{ts}.db")
    if not os.path.exists(DB_PATH):
        print(f"ERROR: database not found at {DB_PATH}")
        sys.exit(1)
    shutil.copy2(DB_PATH, path)
    size = os.path.getsize(path)
    print(f"Backup saved: {path} ({size:,} bytes)")
    return path


def restore(path: str) -> None:
    if not os.path.exists(path):
        print(f"ERROR: backup not found at {path}")
        sys.exit(1)
    # Safety: rename current to .old before overwriting
    if os.path.exists(DB_PATH):
        old_path = DB_PATH + ".old"
        shutil.move(DB_PATH, old_path)
        print(f"Existing DB moved to {old_path}")
    shutil.copy2(path, DB_PATH)
    print(f"Restored {path} → {DB_PATH}")


def list_backups() -> list[dict]:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    backups = []
    for f in sorted(os.listdir(BACKUP_DIR)):
        fp = os.path.join(BACKUP_DIR, f)
        if os.path.isfile(fp):
            backups.append({
                "filename": f,
                "size_bytes": os.path.getsize(fp),
                "modified": datetime.datetime.fromtimestamp(
                    os.path.getmtime(fp)
                ).isoformat(),
            })
    return backups


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: py -m scripts.backup [backup|restore|list] [path]")
        sys.exit(1)

    cmd = sys.argv[1]
    arg = sys.argv[2] if len(sys.argv) > 2 else None

    if cmd == "backup":
        backup(arg)
    elif cmd == "restore":
        if not arg:
            print("Usage: py -m scripts.backup restore <path>")
            sys.exit(1)
        restore(arg)
    elif cmd == "list":
        for b in list_backups():
            print(f"{b['filename']:40s} {b['size_bytes']:>10,} bytes  {b['modified']}")
    else:
        print(f"Unknown command: {cmd}")
