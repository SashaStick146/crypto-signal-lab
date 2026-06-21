"""HTML-отчёт: текущие сетапы (уровни TP/SL + ML) + послужной список + журнал с исходами."""
import time, html, json
from pathlib import Path
from . import track, ml

REPORT_PATH = Path(__file__).resolve().parent.parent / "report.html"


def _pct(v): return f"{v:+.1%}" if isinstance(v, (int, float)) else "—"
def _wr(v): return f"{v:.0%}" if isinstance(v, (int, float)) else "н/д"


def render(conn, out_path=REPORT_PATH):
    ts = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    st = track.stats(conn); model = ml.train(conn)
    cur = conn.execute("SELECT * FROM signals WHERE graded=0 AND ts=(SELECT MAX(ts) FROM signals)").fetchall()

    def ml_prob(row):
        try: return ml.predict(model, json.loads(row["features"] or "{}"))
        except Exception: return None
    cur = sorted(cur, key=lambda s: -((ml_prob(s) if ml_prob(s) is not None else st.get(s["kind"], {}).get("avg_ret", -9))))

    cur_rows = []
    for s in cur:
        ks = st.get(s["kind"], {}); p = ml_prob(s)
        dc = "#5fd38a" if s["direction"] == "long" else "#d64545"
        ml_cell = f"{p:.0%}" if p is not None else "—"
        lvl = (f"<span style='color:#5fd38a'>+{s['tp_pct']:.1%}</span> / <span style='color:#d64545'>−{s['sl_pct']:.1%}</span>"
               if s["tp_pct"] is not None else "—")
        proven = (f"винрейт {_wr(ks.get('winrate'))}, ср.дох {_pct(ks.get('avg_ret'))} (n={ks.get('n')})" if ks else "нет статистики")
        cur_rows.append(
            f"<tr><td><b>{html.escape(s['symbol'])}</b></td><td>{html.escape(s['kind'])}</td>"
            f"<td style='color:{dc}'>{s['direction']}</td><td>{s['entry']:.4g}</td><td>{lvl}</td>"
            f"<td><b style='color:#e0b341'>{ml_cell}</b></td><td>{proven}</td></tr>")

    krows = sorted(st.items(), key=lambda kv: -kv[1]["avg_ret"])
    track_rows = [f"<tr><td>{html.escape(k)}</td><td>{v['n']}</td><td>{_wr(v['winrate'])}</td>"
                  f"<td style='color:{'#5fd38a' if v['avg_ret']>0 else '#d64545'}'>{_pct(v['avg_ret'])}</td></tr>"
                  for k, v in krows]

    jrows = conn.execute("""SELECT symbol,kind,direction,entry,ts,graded,hit,outcome,mfe
                            FROM signals ORDER BY ts DESC, rowid DESC LIMIT 30""").fetchall()
    jr = []
    for r in jrows:
        when = time.strftime("%m-%d %H:%M", time.gmtime(int(r["ts"] or 0)/1000))
        dc = "#5fd38a" if r["direction"] == "long" else "#d64545"
        peak = _pct(r["mfe"]) if r["mfe"] is not None else "—"
        if not r["graded"]:
            res = "⏳ зреет"
        elif r["hit"] == "TP":
            res = f"✅ TP {_pct(r['outcome'])}"
        elif r["hit"] == "SL":
            res = f"❌ SL {_pct(r['outcome'])}"
        else:
            res = f"⏱ {_pct(r['outcome'])}"
        jr.append(f"<tr><td>{when}</td><td><b>{html.escape(r['symbol'])}</b></td><td>{html.escape(r['kind'])}</td>"
                  f"<td style='color:{dc}'>{r['direction']}</td><td>{r['entry']:.4g}</td><td>{peak}</td><td>{res}</td></tr>")

    n_graded = conn.execute("SELECT COUNT(*) c FROM signals WHERE graded=1").fetchone()["c"]
    n_total = conn.execute("SELECT COUNT(*) c FROM signals").fetchone()["c"]
    ml_status = (f"🤖 ML-модель обучена на {model['n']} проверенных сигналах и активна."
                 if model.get("ready") else
                 f"🤖 ML-модель копит данные: {model.get('n',0)}/{ml.MIN_TRAIN} (это порог ВКЛЮЧЕНИЯ; дальше учится постоянно).")

    doc = f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Crypto Signal Lab</title>
<style>
  body {{ font-family:system-ui,sans-serif; margin:0; background:#0e0f13; color:#e8e8ea; }}
  .wrap {{ max-width:1050px; margin:0 auto; padding:24px; }}
  h1 {{ font-size:22px; }} h2 {{ font-size:16px; margin-top:30px; }}
  .sub {{ color:#9aa0a6; font-size:13px; margin-bottom:16px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th,td {{ text-align:left; padding:8px 10px; border-bottom:1px solid #23252b; }}
  th {{ color:#9aa0a6; }} b {{ color:#8ab4f8; }}
  .note {{ background:#1c1e24; border-left:3px solid #e0883a; padding:10px 14px; border-radius:4px;
           font-size:12px; color:#cfd2d6; margin:16px 0; }}
</style></head><body><div class="wrap">
  <h1>📡 Crypto Signal Lab</h1>
  <div class="sub">Обновлено: {ts} · сигналов в журнале: {n_total} · оценено исходов: {n_graded}</div>
  <div class="note">{ml_status}<br>Исход считается по ПУТИ цены за {track.HORIZON_H}ч: что задето первым —
  тейк-профит (TP) или стоп-лосс (SL). Уровни адаптивны к волатильности монеты (ATR).</div>

  <h2>🎯 Текущие сетапы</h2>
  <table>
    <tr><th>Монета</th><th>Сигнал</th><th>Прогноз</th><th>Цена</th><th>Тейк / Стоп</th><th>ML-шанс</th><th>Историческая сила</th></tr>
    {''.join(cur_rows) or '<tr><td colspan=7>Сейчас активных сетапов нет.</td></tr>'}
  </table>

  <h2>📚 Послужной список сигналов</h2>
  <div class="sub">Чем больше «n», тем надёжнее. Положительная ср. доходность = тип сигнала работает.</div>
  <table>
    <tr><th>Тип сигнала</th><th>Проверено (n)</th><th>Винрейт</th><th>Ср. доходность</th></tr>
    {''.join(track_rows) or '<tr><td colspan=4>Пока нет оценённых исходов — нужно накопить историю.</td></tr>'}
  </table>

  <h2>🗒 Последние записи журнала</h2>
  <div class="sub">«Пик» — макс. плюс, которого достигала сделка. ⏳ зреет · ✅ TP · ❌ SL · ⏱ закрытие по времени.</div>
  <table>
    <tr><th>Время (UTC)</th><th>Монета</th><th>Сигнал</th><th>Прогноз</th><th>Цена</th><th>Пик</th><th>Итог</th></tr>
    {''.join(jr) or '<tr><td colspan=7>Журнал пуст.</td></tr>'}
  </table>
</div></body></html>"""
    Path(out_path).write_text(doc, encoding="utf-8")
    return Path(out_path)
