"""Telegram-сводка каждые 4 часа: текущие сетапы + статус обучения (по желанию)."""
import os, json, logging
from . import track, ml
log = logging.getLogger("alerts")
MAX_SETUPS = 8


def send(conn):
    token = os.getenv("TELEGRAM_TOKEN"); chat = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        log.info("Telegram не настроен — сводка не отправлена."); return
    import requests
    st = track.stats(conn); model = ml.train(conn)
    cur = conn.execute("SELECT * FROM signals WHERE graded=0 AND ts=(SELECT MAX(ts) FROM signals)").fetchall()

    def ml_prob(row):
        try: return ml.predict(model, json.loads(row["features"] or "{}"))
        except Exception: return None
    cur = sorted(cur, key=lambda s: -((ml_prob(s) if ml_prob(s) is not None else st.get(s["kind"], {}).get("avg_ret", -9))))

    lines = ["📡 Crypto Signal Lab — сводка", f"Сетапов сейчас: {len(cur)}"]
    for s in cur[:MAX_SETUPS]:
        p = ml_prob(s); ks = st.get(s["kind"])
        ml_str = f"ML {p:.0%}" if p is not None else "ML —"
        hist = f"истор. {ks['avg_ret']:+.1%}" if ks else "нет статистики"
        lines.append(f"• {s['symbol']} — {s['kind']} ({s['direction']}) @{s['entry']:.4g} · {ml_str} · {hist}")
    if len(cur) > MAX_SETUPS:
        lines.append(f"…и ещё {len(cur) - MAX_SETUPS}")
    n_graded = conn.execute("SELECT COUNT(*) c FROM signals WHERE graded=1").fetchone()["c"]
    n_total = conn.execute("SELECT COUNT(*) c FROM signals").fetchone()["c"]
    ml_state = "обучена" if model.get("ready") else f"копит данные {model.get('n',0)}/{ml.MIN_TRAIN}"
    lines.append(f"Журнал: {n_total} сигналов, оценено {n_graded}. ML: {ml_state}.")
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat, "text": "\n".join(lines), "disable_web_page_preview": "true"}, timeout=30)
        log.info("Сводка отправлена (%s сетапов).", len(cur))
    except requests.RequestException as e:
        log.warning("Не удалось отправить сводку: %s", e)
