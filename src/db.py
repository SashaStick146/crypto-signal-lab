"""База (SQLite): свечи, фандинг, лонг/шорт, журнал сигналов с исходами."""
import os, sqlite3, json
from pathlib import Path
DB_PATH = Path(os.getenv("LAB_DB", Path(__file__).resolve().parent.parent / "data" / "lab.db"))


def connect(db_path=DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(db_path); c.row_factory = sqlite3.Row
    c.executescript("""
    CREATE TABLE IF NOT EXISTS candles(symbol TEXT, ts INTEGER, o REAL,h REAL,l REAL,c REAL,vol REAL,
        PRIMARY KEY(symbol,ts));
    CREATE TABLE IF NOT EXISTS funding(symbol TEXT, ts INTEGER, rate REAL, PRIMARY KEY(symbol,ts));
    CREATE TABLE IF NOT EXISTS lsr(symbol TEXT, ts INTEGER, ratio REAL, PRIMARY KEY(symbol,ts));
    CREATE TABLE IF NOT EXISTS signals(
        id TEXT PRIMARY KEY, symbol TEXT, ts INTEGER, kind TEXT, direction TEXT,
        entry REAL, horizon_h INTEGER, outcome REAL, win INTEGER, graded INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
    CREATE INDEX IF NOT EXISTS idx_candles ON candles(symbol,ts);
    CREATE INDEX IF NOT EXISTS idx_sig_kind ON signals(kind);
    """)
    c.commit(); return c


def upsert_candles(conn, symbol, rows):
    data = []
    for r in rows:
        ts = int(r[0])
        data.append((symbol, ts, float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])))
    conn.executemany("INSERT OR IGNORE INTO candles(symbol,ts,o,h,l,c,vol) VALUES (?,?,?,?,?,?,?)", data)
    conn.commit(); return len(data)


def upsert_funding(conn, symbol, ts, rate):
    conn.execute("INSERT OR IGNORE INTO funding(symbol,ts,rate) VALUES (?,?,?)", (symbol, int(ts), float(rate)))
    conn.commit()


def upsert_lsr(conn, symbol, rows):
    data = [(symbol, int(r[0]), float(r[1])) for r in rows]
    conn.executemany("INSERT OR IGNORE INTO lsr(symbol,ts,ratio) VALUES (?,?,?)", data); conn.commit()


def last_closes(conn, symbol, n=200):
    rows = conn.execute("SELECT ts,o,h,l,c,vol FROM candles WHERE symbol=? ORDER BY ts DESC LIMIT ?",
                        (symbol, n)).fetchall()
    return list(reversed(rows))


def latest_funding(conn, symbol):
    r = conn.execute("SELECT rate FROM funding WHERE symbol=? ORDER BY ts DESC LIMIT 1", (symbol,)).fetchone()
    return r["rate"] if r else None


def latest_lsr(conn, symbol):
    r = conn.execute("SELECT ratio FROM lsr WHERE symbol=? ORDER BY ts DESC LIMIT 1", (symbol,)).fetchone()
    return r["ratio"] if r else None


def price_at_or_after(conn, symbol, ts):
    r = conn.execute("SELECT c FROM candles WHERE symbol=? AND ts>=? ORDER BY ts ASC LIMIT 1", (symbol, ts)).fetchone()
    return r["c"] if r else None


def get_meta(conn, k, d=None):
    r = conn.execute("SELECT value FROM meta WHERE key=?", (k,)).fetchone()
    return json.loads(r["value"]) if r else d


def set_meta(conn, k, v):
    conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", (k, json.dumps(v))); conn.commit()
