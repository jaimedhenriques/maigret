"""Offline encrypted backup/restore and retention tools. Run against stopped restore targets."""
import argparse
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from cryptography.fernet import Fernet


def backup(database, target, key):
    """SQLite online backup is consistent while the application writes."""
    cipher=Fernet(key)
    target=Path(target)
    with tempfile.TemporaryDirectory() as directory:
        snapshot=Path(directory)/'snapshot.sqlite3'
        with sqlite3.connect(f'file:{Path(database).resolve()}?mode=ro',uri=True) as source, sqlite3.connect(snapshot) as destination:
            source.backup(destination)
            if destination.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('Backup integrity check failed')
        encrypted=cipher.encrypt(snapshot.read_bytes())
    target.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive create prevents overwriting a previous good backup.
    with target.open('xb') as output:
        target.chmod(0o600);output.write(encrypted);output.flush();os.fsync(output.fileno())
    return target


def restore(archive,target,key):
    """Refuse overwrites; validate decrypted DB before committing a restore."""
    target=Path(target)
    if target.exists():raise ValueError('Restore target must not exist')
    raw=Fernet(key).decrypt(Path(archive).read_bytes())
    target.parent.mkdir(parents=True,exist_ok=True)
    try:
        with target.open('xb') as output:target.chmod(0o600);output.write(raw)
        with sqlite3.connect(target) as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchone():raise ValueError('Restore validation failed')
    except Exception:
        target.unlink(missing_ok=True);raise
    return target


def retention_candidates(database,days=90):
    if not 1<=days<=3650:raise ValueError('Retention must be 1 to 3650 days')
    cutoff=(datetime.now(timezone.utc)-timedelta(days=days)).isoformat(timespec='seconds')
    with sqlite3.connect(f'file:{Path(database).resolve()}?mode=ro',uri=True) as db:
        # Dry-run only: operator checks legal holds, provider deletion and backup expiration.
        return db.execute("SELECT id,tenant_id,status,updated_at FROM candidates WHERE sample=0 AND status IN ('completed','withdrawn') AND updated_at<?",(cutoff,)).fetchall()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['backup','restore','retention-report'])
    parser.add_argument('--database',default=os.environ.get('VETRA_DATABASE','/data/vetra.sqlite3'))
    parser.add_argument('--file');parser.add_argument('--days',type=int,default=90)
    args=parser.parse_args()
    if args.action=='retention-report':
        for row in retention_candidates(args.database,args.days):print('\t'.join(row))
    else:
        if not args.file:parser.error('--file is required')
        key=os.environ.get('VETRA_BACKUP_KEY','')
        if not key:parser.error('VETRA_BACKUP_KEY is required; store it separately from backups')
        if args.action=='backup':backup(args.database,args.file,key)
        else:restore(args.file,args.database,key)
        print(args.action+' completed and integrity checked')

if __name__=='__main__':main()
