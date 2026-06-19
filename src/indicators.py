"""Технические индикаторы из списка свечей."""
import statistics


def rsi(closes, period=14):
    if len(closes) < period + 1: return None
    gains, losses = [], []
    for i in range(-period, 0):
        ch = closes[i] - closes[i - 1]
        gains.append(max(ch, 0)); losses.append(max(-ch, 0))
    ag = sum(gains) / period; al = sum(losses) / period
    if al == 0: return 100.0
    rs = ag / al
    return 100 - 100 / (1 + rs)


def vol_zscore(vols):
    if len(vols) < 25: return None
    hist = vols[-25:-1]; last = vols[-1]
    m = statistics.mean(hist); sd = statistics.pstdev(hist)
    return (last - m) / sd if sd > 0 else None


def ret_over(closes, n):
    if len(closes) < n + 1: return None
    return closes[-1] / closes[-1 - n] - 1
