"""
Клиент к публичному API Bybit v5 (без ключей). Свечи, фандинг, лонг/шорт.
Нормализует ответы к тому же виду, что ждёт остальная программа:
  candles -> [[ts,o,h,l,c,vol], ...]
  funding -> {"rate": float, "ts": ms}
  long_short_ratio -> [[ts, ratio], ...]   (ratio = buyRatio/sellRatio)
"""
import time, logging
import requests
BASE = "https://api.bybit.com"
log = logging.getLogger("bybit")


class Bybit:
    def __init__(self, pause=0.2, timeout=30, retries=4):
        self.pause = pause; self.timeout = timeout; self.retries = retries
        self.s = requests.Session(); self.s.headers.update({"User-Agent": "signal-lab/1.0"})

    def _get(self, path, params):
        for a in range(1, self.retries + 1):
            try:
                r = self.s.get(BASE + path, params=params, timeout=self.timeout)
                if r.status_code == 429:
                    time.sleep(self.pause * 2 ** a); continue
                r.raise_for_status(); time.sleep(self.pause)
                j = r.json()
                return (j.get("result") or {}).get("list", []) if isinstance(j, dict) else []
            except requests.RequestException as e:
                log.warning("Bybit %s попытка %s: %s", path, a, e); time.sleep(self.pause * 2 ** a)
        return []

    def candles(self, symbol, interval="60", limit=200):
        rows = self._get("/v5/market/kline",
                         {"category": "linear", "symbol": symbol, "interval": interval, "limit": limit})
        # Bybit: [start, open, high, low, close, volume, turnover] (новые сверху)
        return [[r[0], r[1], r[2], r[3], r[4], r[5]] for r in rows]

    def funding(self, symbol):
        rows = self._get("/v5/market/tickers", {"category": "linear", "symbol": symbol})
        if not rows:
            return None
        t = rows[0]
        fr = t.get("fundingRate")
        if fr in (None, ""):
            return None
        return {"rate": float(fr), "ts": int(t.get("nextFundingTime") or time.time() * 1000)}

    def long_short_ratio(self, symbol, period="1h"):
        rows = self._get("/v5/market/account-ratio",
                         {"category": "linear", "symbol": symbol, "period": period, "limit": 50})
        out = []
        for r in rows:
            try:
                buy = float(r.get("buyRatio")); sell = float(r.get("sellRatio"))
                if sell > 0:
                    out.append([int(r.get("timestamp")), buy / sell])
            except (TypeError, ValueError):
                continue
        return out
