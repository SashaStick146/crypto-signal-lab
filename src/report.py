"""HTML-отчёт: текущие сетапы (ML + доказанная сила) + послужной список."""
import time, html
from pathlib import Path
from . import track, ml

REPORT_PATH = Path(__file__).resolve().parent.parent / "report.html"


def _pct(v): return f"{v:+.1%}" if isinstance(v, (int, float)) else "—"
def _wr(v): return f"{v:.0%}" if isinstance(v, (int, float)) else "н/д"


def render(conn, out_path=REPORT_PATH):
    ts = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    st = track.stats(conn)
    model = ml.train(conn)

    import json
    cur = conn.execute(
        "SELECT * FROM signals WHERE graded=0 AND ts=(SELECT MAX(ts) FROM signals)").fetchall()

    def ml_prob(row):
        try:
            return ml.predict(model, json.loads(row["features"] or "{}"))
        except Exception:
            return None

    def sort_key(s):
        p = ml_prob(s)
        return -(p if p is not None else st.get(s["kind"], {}).get("avg_ret", -9))
    cur = sorted(cur, key=sort_key)

    cur_rows = []
    for s in cur:
        k = s["kind"]; ks = st.get(k, {})
        dir_color = "#5fd38a" if s["direction"] == "long" else "#d64545"
        p = ml_prob(s)
        ml_cell = f"{p:.0%}" if p is not None else "—"
        proven = (f"винрейт {_wr(ks.get('winrate'))}, ср.дох {_pct(ks.get('avg_ret'))} (n={ks.get('n')})"
                  if ks else "нет статистики")
        cur_rows.append(
            f"<tr><td><b>{html.escape(s['symbol'])}</b></td><td>{html.escape(k)}</td>"
            f"<td style='color:{dir_color}'>{s['direction']}</td><td>{s['entry']:.4g}</td>"
            f"<td><b style='color:#e0b341'>{ml_cell}</b></td><td>{proven}</td></tr>")

    krows = sorted(st.items(), key=lambda kv: -kv[1]["avg_ret"])
    track_rows = []
    for k, v in krows:
        color = "#5fd38a" if v["avg_ret"] > 0 else "#d64545"
        track_rows.append(f"<tr><td>{html.escape(k)}</td><td>{v['n']}</td>"
                          f"<td>{_wr(v['winrate'])}</td><td style='color:{color}'>{_pct(v['avg_ret'])}</td></tr>")

    n_graded = conn.execute("SELECT COUNT(*) c FROM signals WHERE graded=1").fetchone()["c"]
    n_total = conn.execute("SELECT COUNT(*) c FROM signals").fetchone()["c"]
    if model.get("ready"):
        ml_status = f"🤖 ML-модель обучена на {model['n']} проверенных сигналах и активна."
    else:
        ml_status = (f"🤖 ML-модель копит данные: {model.get('n',0)}/{ml.MIN_TRAIN} проверенных сигналов. "
                     f"Колонка ML заработает, когда наберётся достаточно.")

    doc = f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Crypto Signal Lab</title>
<style>
  body {{ font-family:system-ui,sans-serif; margin:0; background:#0e0f13; color:#e8e8ea; }}
  .wrap {{ max-width:1000px; margin:0 auto; padding:24px; }}
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
  <div class="note">{ml_status}<br>Программа учится сама: каждый сигнал проверяется через
  {track.HORIZON_H}ч. Колонка <b>ML</b> — вероятность успеха по обученной модели.</div>

  <h2>🎯 Текущие сетапы</h2>
  <table>
    <tr><th>Монета</th><th>Сигнал</th><th>Прогноз</th><th>Цена</th><th>ML-шанс</th><th>Историческая сила</th></tr>
    {''.join(cur_rows) or '<tr><td colspan=6>Сейчас активных сетапов нет.</td></tr>'}
  </table>

  <h2>📚 Послужной список сигналов</h2>
  <div class="sub">Чем больше «n», тем надёжнее. Положительная ср. доходность = тип сигнала работает.</div>
  <table>
    <tr><th>Тип сигнала</th><th>Проверено (n)</th><th>Винрейт</th><th>Ср. доходность за {track.HORIZON_H}ч</th></tr>
    {''.join(track_rows) or '<tr><td colspan=4>Пока нет оценённых исходов — нужно накопить историю.</td></tr>'}
  </table>
</div></body></html>"""
    Path(out_path).write_text(doc, encoding="utf-8")
    return Path(out_path)
