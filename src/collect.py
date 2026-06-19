"""Сбор данных по списку монет с Bybit: свечи, фандинг, лонг/шорт."""
import logging
from . import db
from .bybit import Bybit
log = logging.getLogger("collect")

# Топ ликвидных монет (USDT-перпетуалы Bybit). Меняй список по вкусу.
COINS = ["BTC","ETH","SOL","XRP","BNB","DOGE","ADA","AVAX","LINK","TON",
         "TRX","DOT","NEAR","LTC","BCH","APT","ARB","OP","SUI",
         "INJ","SEI","TIA","PEPE","WIF","WLD"]


def run(conn, interval="60", period="1h"):
    api = Bybit()
    for ccy in COINS:
        sym = f"{ccy}USDT"
        candles = api.candles(sym, interval=interval, limit=200)
        if candles:
            db.upsert_candles(conn, ccy, candles)
        f = api.funding(sym)
        if f:
            db.upsert_funding(conn, ccy, f["ts"], f["rate"])
        ls = api.long_short_ratio(sym, period=period)
        if ls:
            db.upsert_lsr(conn, ccy, ls)
        log.info("%s: свечей=%s фандинг=%s lsr=%s", ccy, len(candles), bool(f), len(ls))
    return len(COINS)
