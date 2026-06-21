"""Журнал + оценка по ПУТИ цены: первое касание TP/SL, пик (MFE) и просадка (MAE)."""
import json
from . import db

HORIZON_H = 24


def record(conn, fired):
    new = 0
    for s in fired:
        sid = f"{s['symbol']}-{s['ts']}-{s['kind']}"
        if conn.execute("SELECT 1 FROM signals WHERE id=?", (sid,)).fetchone() is None:
            conn.execute("""INSERT INTO signals(id,symbol,ts,kind,direction,entry,horizon_h,graded,
                            tp_price,sl_price,tp_pct,sl_pct,mfe,mae,features)
                            VALUES (?,?,?,?,?,?,?,0,?,?,?,?,0,0,?)""",
                         (sid, s["symbol"], s["ts"], s["kind"], s["direction"], s["entry"], HORIZON_H,
                          s["tp_price"], s["sl_price"], s["tp_pct"], s["sl_pct"],
                          json.dumps(s.get("features") or {})))
            new += 1
    conn.commit(); return new


def update_open(conn, now_ms):
    """Каждый запуск: обновляем путь открытых сигналов, закрываем по TP/SL/таймауту."""
    rows = conn.execute("SELECT * FROM signals WHERE graded=0").fetchall()
    closed = 0
    for s in rows:
        entry = s["entry"]; long = (s["direction"] == "long")
        window_end = s["ts"] + s["horizon_h"]*3600*1000
        cands = db.candles_between(conn, s["symbol"], s["ts"], min(now_ms, window_end))
        if not cands:
            continue
        mfe = s["mfe"] or 0.0; mae = s["mae"] or 0.0
        has_levels = s["tp_price"] is not None and s["sl_price"] is not None
        hit = None
        for cnd in cands:
            h = cnd["h"]; l = cnd["l"]
            ret_h = h/entry - 1; ret_l = l/entry - 1
            fav = ret_h if long else -ret_l
            adv = ret_l if long else -ret_h
            mfe = max(mfe, fav); mae = min(mae, adv)
            if not has_levels:
                continue
            if long:
                tp_touch = h >= s["tp_price"]; sl_touch = l <= s["sl_price"]
            else:
                tp_touch = l <= s["tp_price"]; sl_touch = h >= s["sl_price"]
            if sl_touch:        # консервативно: при двойном касании считаем стоп
                hit = "SL"; break
            if tp_touch:
                hit = "TP"; break
        if hit == "TP":
            out, win = s["tp_pct"], 1
        elif hit == "SL":
            out, win = -s["sl_pct"], 0
        elif now_ms >= window_end:
            last_c = cands[-1]["c"]; ret = last_c/entry - 1
            out = ret if long else -ret; win = 1 if out > 0 else 0; hit = "TIME"
        else:
            # ещё открыт — только обновим путь
            conn.execute("UPDATE signals SET mfe=?, mae=? WHERE id=?", (mfe, mae, s["id"]))
            continue
        conn.execute("UPDATE signals SET graded=1, outcome=?, win=?, hit=?, mfe=?, mae=? WHERE id=?",
                     (out, win, hit, mfe, mae, s["id"]))
        closed += 1
    conn.commit(); return closed


def stats(conn):
    rows = conn.execute("""SELECT kind, COUNT(*) n, SUM(win) wins, AVG(outcome) avg_ret
                           FROM signals WHERE graded=1 GROUP BY kind""").fetchall()
    return {r["kind"]: {"n": r["n"], "winrate": (r["wins"] or 0)/r["n"] if r["n"] else None,
                        "avg_ret": r["avg_ret"] or 0.0} for r in rows}
