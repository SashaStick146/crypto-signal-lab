"""Технические индикаторы."""
import statistics


def rsi(closes, period=14):
    if len(closes) < period + 1: return None
    g = l = 0.0
    for i in range(-period, 0):
        ch = closes[i] - closes[i-1]
        g += max(ch, 0); l += max(-ch, 0)
    ag = g/period; al = l/period
    if al == 0: return 100.0
    return 100 - 100/(1 + ag/al)


def vol_zscore(vols):
    if len(vols) < 25: return None
    hist = vols[-25:-1]; m = statistics.mean(hist); sd = statistics.pstdev(hist)
    return (vols[-1]-m)/sd if sd > 0 else None


def ret_over(closes, n):
    if len(closes) < n+1: return None
    return closes[-1]/closes[-1-n] - 1


def sma(closes, period):
    if len(closes) < period: return None
    return sum(closes[-period:])/period


def atr(highs, lows, closes, period=14):
    """Средний истинный диапазон — мера волатильности (в цене)."""
    if len(closes) < period + 1: return None
    trs = []
    for i in range(-period, 0):
        tr = max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
        trs.append(tr)
    return sum(trs)/period
