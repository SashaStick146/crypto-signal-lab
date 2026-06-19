"""Сбор данных с Coinbase (свечи с объёмом). Фандинг/лонг-шорт недоступны здесь."""
import logging
from . import db
from .coinbase import Coinbase
log = logging.getLogger("collect")

# Монеты, торгуемые на Coinbase (пара ВАЛЮТА-USD). Меняй по вкусу.
COINS = ["BTC","ETH","SOL","XRP","DOGE","ADA","AVAX","LINK","DOT","LTC",
         "BCH","APT","ARB","OP","SUI","NEAR","INJ","SEI","TIA","PEPE",
         "WIF","ATOM","UNI","AAVE"]


def run(conn, granularity=3600):
    api = Coinbase()
    ok = 0
    for ccy in COINS:
        candles = api.candles(f"{ccy}-USD", granularity=granularity)
        if candles:
            db.upsert_candles(conn, ccy, candles); ok += 1
        log.info("%s: свечей=%s", ccy, len(candles))
    return ok
