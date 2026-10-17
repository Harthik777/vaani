"""Durable local artifacts. Capability keys are stored as SHA-256 hashes."""
import hashlib
import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from services import config

def now():
    return datetime.now(timezone.utc).isoformat()

@contextmanager
def connect():
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(config.DATA_DIR / "vaani.sqlite3")
    db.row_factory = sqlite3.Row
    try:
        db.execute("CREATE TABLE IF NOT EXISTS artifacts (id TEXT PRIMARY KEY, kind TEXT, key_hash TEXT, payload TEXT, content BLOB, mime TEXT)")
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def create(kind, payload, content=None, mime=None, public=False):
    ident, key = secrets.token_urlsafe(18), secrets.token_urlsafe(32)
    with connect() as db:
        db.execute("INSERT INTO artifacts VALUES (?, ?, ?, ?, ?, ?)", (ident, kind, "" if public else hashlib.sha256(key.encode()).hexdigest(), json.dumps(payload, ensure_ascii=False), content, mime))
    return ident, "" if public else key

def get(ident, kind, key="", internal=False):
    with connect() as db:
        row = db.execute("SELECT * FROM artifacts WHERE id=? AND kind=?", (ident, kind)).fetchone()
    if not row or (not internal and row["key_hash"] and not secrets.compare_digest(row["key_hash"], hashlib.sha256(key.encode()).hexdigest())):
        return None
    return {**dict(row), "payload": json.loads(row["payload"])}

def update_ticket(ident, payload):
    # Published documents and evidence deliberately have no update operation.
    with connect() as db:
        db.execute("UPDATE artifacts SET payload=? WHERE id=? AND kind='ticket'", (json.dumps(payload, ensure_ascii=False), ident))
