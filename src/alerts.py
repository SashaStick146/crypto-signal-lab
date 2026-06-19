"""Telegram-алерт о сильных текущих сетапах (по желанию)."""
import os, logging
from . import track
log = logging.getLogger("alerts")

MIN_N = 20            # доверяем типу сигнала, если оценено >= стольких исходов
MIN_EDGE = 0.01       # и средняя доходность >= 1%


def send(conn):
    token = os.getenv("TELEGRAM_TOKEN"); chat = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        log.info("Telegram не настроен."); return
    import requests
    st = track.stats(conn)
    cur = conn.execute("SELECT * FROM signals WHERE graded=0 AND ts=(SELECT MAX(ts) FROM signals)").fetchall()
    strong = []
    for s in cur:
        ks = st.get(s["kind"])
        if ks and ks["n"] >= MIN_N and ks["avg_ret"] >= MIN_EDGE:
            strong.append((s, ks))
    strong.sort(key=lambda x: -x[1]["avg_ret"])
    if not strong:
        log.info("Сильных проверенных сетапов нет."); return
    lines = ["📡 Сильные сетапы (по истории):\n"]
    for s, ks in strong[:15]:
        lines.append(f"• {s['symbol']} — {s['kind']} ({s['direction']})\n"
                     f"  история: винрейт {ks['winrate']:.0%}, ср.дох {ks['avg_ret']:+.1%}, n={ks['n']}")
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat, "text": "\n".join(lines), "disable_web_page_preview": "true"}, timeout=30)
        log.info("Алерт отправлен (%s).", len(strong))
    except requests.RequestException as e:
        log.warning("Не отправлено: %s", e)
