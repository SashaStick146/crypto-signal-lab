"""Поиск текущих сигналов (сетапов) по одной монете."""
from . import db
from .indicators import rsi, vol_zscore, ret_over

# Пороги сигналов (можно крутить)
VOL_Z = 2.5
RSI_LOW, RSI_HIGH = 30, 70
FUND_HIGH, FUND_LOW = 0.0006, -0.0006
LSR_HIGH, LSR_LOW = 2.3, 0.85


def detect(conn, symbol):
    rows = db.last_closes(conn, symbol, 200)
    if len(rows) < 30:
        return []
    closes = [r["c"] for r in rows]; vols = [r["vol"] for r in rows]
    highs = [r["h"] for r in rows]; lows = [r["l"] for r in rows]
    ts = rows[-1]["ts"]; last = rows[-1]
    entry = closes[-1]
    out = []

    def add(kind, direction):
        out.append({"symbol": symbol, "ts": ts, "kind": kind, "direction": direction, "entry": entry})

    vz = vol_zscore(vols)
    if vz is not None and vz >= VOL_Z:
        add("vol_spike_up" if last["c"] >= last["o"] else "vol_spike_down",
            "long" if last["c"] >= last["o"] else "short")

    r = rsi(closes)
    if r is not None:
        if r <= RSI_LOW: add("rsi_oversold", "long")
        elif r >= RSI_HIGH: add("rsi_overbought", "short")

    f = db.latest_funding(conn, symbol)
    if f is not None:
        if f >= FUND_HIGH: add("funding_crowded_long", "short")   # перегрев лонгов -> контр-шорт
        elif f <= FUND_LOW: add("funding_crowded_short", "long")

    ls = db.latest_lsr(conn, symbol)
    if ls is not None:
        if ls >= LSR_HIGH: add("crowd_too_long", "short")
        elif ls <= LSR_LOW: add("crowd_too_short", "long")

    prev_high = max(highs[-25:-1]); prev_low = min(lows[-25:-1])
    if closes[-1] > prev_high: add("breakout_up", "long")
    if closes[-1] < prev_low: add("breakdown", "short")

    return out
