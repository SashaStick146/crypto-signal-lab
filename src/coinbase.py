"""
Клиент к публичному API Coinbase Exchange (без ключей, доступен с GitHub).
Только свечи с объёмом. Нормализует к виду [[ts_ms,o,h,l,c,vol], ...].
"""
import time, logging
import requests
BASE = "https://api.exchange.coinbase.com"
log = logging.getLogger("coinbase")


class Coinbase:
    def __init__(self, pause=0.3, timeout=30, retries=3):
        self.pause = pause; self.timeout = timeout; self.retries = retries
        self.s = requests.Session(); self.s.headers.update({"User-Agent": "signal-lab/1.0"})

    def candles(self, product, granularity=3600):
        # Coinbase: [time(sec), low, high, open, close, volume], новые сверху
        for a in range(1, self.retries + 1):
            try:
                r = self.s.get(f"{BASE}/products/{product}/candles",
                               params={"granularity": granularity}, timeout=self.timeout)
                if r.status_code == 429:
                    time.sleep(self.pause * 2 ** a); continue
                if r.status_code == 404:
                    return []  # такой пары нет на Coinbase
                r.raise_for_status(); time.sleep(self.pause)
                rows = r.json()
                return [[int(x[0]) * 1000, x[3], x[2], x[1], x[4], x[5]] for x in rows]
            except requests.RequestException as e:
                log.warning("Coinbase %s попытка %s: %s", product, a, e); time.sleep(self.pause * 2 ** a)
        return []
