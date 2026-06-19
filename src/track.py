"""Журнал сигналов + самооценка исходов."""
import json
from . import db

HORIZON_H = 24
WIN_THRESHOLD = 0.0


def record(conn, fired):
    new = 0
    for s in fired:
        sid = f"{s['symbol']}-{s['ts']}-{s['kind']}"
        if conn.execute("SELECT 1 FROM signals WHERE id=?", (sid,)).fetchone() is None:
            conn.execute("""INSERT INTO signals(id,symbol,ts,kind,direction,entry,horizon_h,graded,features)
                            VALUES (?,?,?,?,?,?,?,0,?)""",
                         (sid, s["symbol"], s["ts"], s["kind"], s["direction"], s["entry"],
                          HORIZON_H, json.dumps(s.get("features") or {})))
            new += 1
    conn.commit(); return new


def grade(conn, now_ms):
    rows = conn.execute("SELECT * FROM signals WHERE graded=0").fetchall()
    graded = 0
    for s in rows:
        mature = s["ts"] + s["horizon_h"] * 3600 * 1000
        if mature > now_ms:
            continue
        future = db.price_at_or_after(conn, s["symbol"], mature)
        if future is None or not s["entry"]:
            continue
        ret = future / s["entry"] - 1
        signed = ret if s["direction"] == "long" else -ret
        conn.execute("UPDATE signals SET outcome=?, win=?, graded=1 WHERE id=?",
                     (signed, 1 if signed > WIN_THRESHOLD else 0, s["id"]))
        graded += 1
    conn.commit(); return graded


def stats(conn):
    rows = conn.execute("""SELECT kind, COUNT(*) n, SUM(win) wins, AVG(outcome) avg_ret
                           FROM signals WHERE graded=1 GROUP BY kind""").fetchall()
    return {r["kind"]: {"n": r["n"], "winrate": (r["wins"] or 0)/r["n"] if r["n"] else None,
                        "avg_ret": r["avg_ret"] or 0.0} for r in rows}
