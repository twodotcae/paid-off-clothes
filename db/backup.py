"""Consistent backups of paidoff.db.

Uses sqlite3's own backup API, not a file copy. Copying a live SQLite file can capture it
mid-transaction and produce a backup that will not open; the backup API takes a proper snapshot
while the database is in use.

    python3 db/backup.py                  write a timestamped .sqlite into backups/
    python3 db/backup.py --stdout         stream the snapshot to stdout (used by CI and `fly ssh`)
    python3 db/backup.py --verify FILE    check a backup actually opens and holds the catalogue
    python3 db/backup.py --prune 30       delete local backups older than 30 days

A VOLUME IS NOT A BACKUP. Fly volumes live on one physical host; if it fails, backups/ dies with
the database. Pull these off the machine — the deploy workflow keeps one as a build artifact, and
`fly ssh console -C "python3 /app/db/backup.py --stdout" > local.sqlite` gets you one on demand.
"""
import os, sqlite3, sys, time, glob
from datetime import datetime, timedelta

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.abspath(os.environ.get("POC_DATA_DIR", APP_DIR))
DB_PATH = os.path.join(DATA_DIR, "paidoff.db")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")


def snapshot(dest_path):
    """Consistent copy of the live database."""
    src = sqlite3.connect(DB_PATH)
    try:
        dst = sqlite3.connect(dest_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    return dest_path


def verify(path):
    """A backup nobody has restored is a hope, not a backup."""
    c = sqlite3.connect(path)
    try:
        if c.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            return False, "integrity_check failed"
        products = c.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        units = c.execute("SELECT COALESCE(SUM(qty),0) FROM product_sizes").fetchone()[0]
        orders = c.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        if products == 0:
            return False, "no products in the backup"
        return True, f"{products} products, {units} units, {orders} orders"
    except sqlite3.Error as e:
        return False, str(e)
    finally:
        c.close()


def prune(days):
    cutoff = time.time() - days * 86400
    removed = 0
    for p in glob.glob(os.path.join(BACKUP_DIR, "paidoff-*.sqlite")):
        if os.path.getmtime(p) < cutoff:
            os.remove(p)
            removed += 1
    return removed


def main(argv):
    if not os.path.exists(DB_PATH):
        print(f"no database at {DB_PATH}", file=sys.stderr)
        return 1

    if "--stdout" in argv:
        # Snapshot to a temp file first: streaming a live database byte-for-byte is exactly the
        # inconsistency the backup API exists to avoid.
        tmp = os.path.join(BACKUP_DIR, f".stream-{os.getpid()}.sqlite")
        os.makedirs(BACKUP_DIR, exist_ok=True)
        try:
            snapshot(tmp)
            with open(tmp, "rb") as f:
                shutil_copy = f.read()
            sys.stdout.buffer.write(shutil_copy)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        return 0

    if "--verify" in argv:
        target = argv[argv.index("--verify") + 1]
        ok, detail = verify(target)
        print(("OK   " if ok else "FAIL ") + target + " — " + detail)
        return 0 if ok else 1

    if "--prune" in argv:
        days = int(argv[argv.index("--prune") + 1])
        print(f"pruned {prune(days)} backup(s) older than {days} days")
        return 0

    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = os.path.join(BACKUP_DIR, f"paidoff-{stamp}.sqlite")
    snapshot(dest)
    ok, detail = verify(dest)
    size = os.path.getsize(dest)
    print(f"{'OK' if ok else 'FAIL'} {dest} ({size} bytes) — {detail}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
