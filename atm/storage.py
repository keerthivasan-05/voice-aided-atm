"""SQLite persistence: constrained schema and explicit transaction boundaries."""
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path
from .security import hash_pin

SCHEMA = '''
CREATE TABLE IF NOT EXISTS accounts (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, pin_hash TEXT NOT NULL,
 balance_paise INTEGER NOT NULL CHECK(balance_paise >= 0),
 failed_attempts INTEGER NOT NULL DEFAULT 0,
 locked INTEGER NOT NULL DEFAULT 0 CHECK(locked IN (0,1))
);
CREATE TABLE IF NOT EXISTS ledger (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 request_id TEXT UNIQUE NOT NULL,
 account_id TEXT NOT NULL REFERENCES accounts(id),
 kind TEXT NOT NULL CHECK(kind IN ('WITHDRAW','TRANSFER_OUT','TRANSFER_IN')),
 amount_paise INTEGER NOT NULL CHECK(amount_paise > 0),
 counterparty TEXT, balance_after_paise INTEGER NOT NULL,
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS requests (
 request_id TEXT PRIMARY KEY NOT NULL,
 ledger_id INTEGER UNIQUE NOT NULL REFERENCES ledger(id)
);
CREATE TABLE IF NOT EXISTS audit (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 account_id TEXT, event TEXT NOT NULL,
 detail TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_ledger_account ON ledger(account_id,id DESC);
'''


def connect(path):
    db = sqlite3.connect(str(path), timeout=15, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA busy_timeout=15000')
    return db


def initialize(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as db:
        db.execute('PRAGMA journal_mode=WAL')
    with write_transaction(path) as db:
        version = db.execute('PRAGMA user_version').fetchone()[0]
        if version == 0:
            for statement in SCHEMA.strip().rstrip(';').split(';'):
                db.execute(statement)
            # Older callers could reuse an ID across operations. Keep the
            # earliest receipt for each ID and preserve all ledger entries.
            db.execute('''
                INSERT INTO requests(request_id, ledger_id)
                SELECT CASE kind WHEN 'TRANSFER_OUT'
                       THEN substr(request_id, 1, length(request_id) - 4)
                       ELSE request_id END, MIN(id)
                FROM ledger WHERE kind IN ('WITHDRAW', 'TRANSFER_OUT')
                GROUP BY 1
            ''')
            db.execute('PRAGMA user_version=1')
        elif version != 1:
            raise RuntimeError(f'Unsupported database schema version: {version}')


def seed_demo(path):
    """Opt-in sample accounts; never silently overwrite existing balances."""
    initialize(path)
    with write_transaction(path) as db:
        for account_id, name, pin, balance in (
            ('1001', 'Demo Customer One', '1234', 5000000),
            ('1002', 'Demo Customer Two', '5678', 1500000),
        ):
            if not db.execute('SELECT 1 FROM accounts WHERE id=?', (account_id,)).fetchone():
                db.execute('INSERT INTO accounts(id,name,pin_hash,balance_paise) VALUES (?,?,?,?)',
                           (account_id, name, hash_pin(pin), balance))


@contextmanager
def write_transaction(path):
    db = connect(path)
    try:
        db.execute('BEGIN IMMEDIATE')
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
