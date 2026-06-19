#!/usr/bin/env python3
"""Цикл: сбор -> сигналы -> запись -> оценка -> очистка -> отчёт -> алерт."""
import time, logging
from src import db, collect, signals, track, report, alerts
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")


def main():
    conn = db.connect()
    collect.run(conn)
    fired = []
    for ccy in collect.COINS:
        fired += signals.detect(conn, ccy)
    new = track.record(conn, fired)
    graded = track.grade(conn, int(time.time() * 1000))
    removed = db.prune_candles(conn, keep_days=20)   # авто-очистка старых свечей
    report.render(conn)
    alerts.send(conn)
    print(f"Сигналов сейчас: {len(fired)} (новых: {new}). Оценено исходов: {graded}. "
          f"Очищено старых свечей: {removed}.")


if __name__ == "__main__":
    main()
