#!/usr/bin/env python3
"""Цикл: сбор -> сигналы -> запись -> оценка пути (TP/SL) -> очистка -> отчёт -> сводка."""
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
    closed = track.update_open(conn, int(time.time() * 1000))
    removed = db.prune_candles(conn, keep_days=20)
    report.render(conn)
    alerts.send(conn)
    print(f"Сигналов сейчас: {len(fired)} (новых: {new}). Закрыто исходов: {closed}. Очищено свечей: {removed}.")


if __name__ == "__main__":
    main()
