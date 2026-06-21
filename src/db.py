"""База (SQLite)."""
import os, sqlite3, json
from pathlib import Path
DB_PATH = Path(os.getenv("LAB_DB", Path(__file__).resolve().parent.parent / "data" / "lab.db"))
NEW_COLS = {"tp_price":"REAL","sl_price":"REAL","tp_pct":"REAL","sl_pct":"REAL",
            "mfe":"REAL","mae":"REAL","hit":"TEXT","features":"TEXT"}


def connect(db_path=DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(db_path); c.row_factory = sqlite3.Row
    c.executescript("""
    CREATE TABLE IF NOT EXISTS candles(symbol TEXT,ts INTEGER,o REAL,h REAL,l REAL,c REAL,vol REAL,PRIMARY KEY(symbol,ts));
    CREATE TABLE IF NOT EXISTS funding(symbol TEXT,ts INTEGER,rate REAL,PRIMARY KEY(symbol,ts));
    CREATE TABLE IF NOT EXISTS lsr(symbol TEXT,ts INTEGER,ratio REAL,PRIMARY KEY(symbol,ts));
    CREATE TABLE IF NOT EXISTS signals(id TEXT PRIMARY KEY,symbol TEXT,ts INTEGER,kind TEXT,direction TEXT,
        entry REAL,horizon_h INTEGER,outcome REAL,win INTEGER,graded INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT);
    CREATE INDEX IF NOT EXISTS idx_candles ON candles(symbol,ts);
    """)
    have = [r[1] for r in c.execute("PRAGMA table_info(signals)")]
    for col, typ in NEW_COLS.items():
        if col not in have:
            c.execute(f"ALTER TABLE signals ADD COLUMN {col} {typ}")
    c.commit(); return c


def upsert_candles(conn, symbol, rows):
    data = [(symbol,int(r[0]),float(r[1]),float(r[2]),float(r[3]),float(r[4]),float(r[5])) for r in rows]
    conn.executemany("INSERT OR IGNORE INTO candles(symbol,ts,o,h,l,c,vol) VALUES (?,?,?,?,?,?,?)", data)
    conn.commit(); return len(data)


def prune_candles(conn, keep_days=20):
    import time
    cutoff = int((time.time()-keep_days*86400)*1000)
    n = conn.execute("DELETE FROM candles WHERE ts < ?", (cutoff,)).rowcount
    conn.execute("DELETE FROM lsr WHERE ts < ?", (cutoff,)); conn.commit(); return n


def upsert_funding(conn, symbol, ts, rate):
    conn.execute("INSERT OR IGNORE INTO funding(symbol,ts,rate) VALUES (?,?,?)", (symbol,int(ts),float(rate))); conn.commit()


def upsert_lsr(conn, symbol, rows):
    conn.executemany("INSERT OR IGNORE INTO lsr(symbol,ts,ratio) VALUES (?,?,?)",
                     [(symbol,int(r[0]),float(r[1])) for r in rows]); conn.commit()


def last_closes(conn, symbol, n=200):
    rows = conn.execute("SELECT ts,o,h,l,c,vol FROM candles WHERE symbol=? ORDER BY ts DESC LIMIT ?", (symbol,n)).fetchall()
    return list(reversed(rows))


def candles_between(conn, symbol, ts_from, ts_to):
    return conn.execute("SELECT ts,h,l,c FROM candles WHERE symbol=? AND ts>? AND ts<=? ORDER BY ts ASC",
                        (symbol, ts_from, ts_to)).fetchall()


def latest_funding(conn, symbol):
    r = conn.execute("SELECT rate FROM funding WHERE symbol=? ORDER BY ts DESC LIMIT 1", (symbol,)).fetchone()
    return r["rate"] if r else None


def latest_lsr(conn, symbol):
    r = conn.execute("SELECT ratio FROM lsr WHERE symbol=? ORDER BY ts DESC LIMIT 1", (symbol,)).fetchone()
    return r["ratio"] if r else None


def get_meta(conn, k, d=None):
    r = conn.execute("SELECT value FROM meta WHERE key=?", (k,)).fetchone()
    return json.loads(r["value"]) if r else d


def set_meta(conn, k, v):
    conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", (k, json.dumps(v))); conn.commit()
