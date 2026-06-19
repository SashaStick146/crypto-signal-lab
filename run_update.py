#!/usr/bin/env python3
"""Один цикл: собрать данные -> найти сигналы -> записать -> оценить созревшие -> отчёт -> алерт."""
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
    report.render(conn)
    alerts.send(conn)
    print(f"Найдено сигналов сейчас: {len(fired)} (новых записано: {new}). "
          f"Оценено новых исходов: {graded}.")


if __name__ == "__main__":
    main()
