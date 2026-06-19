"""
Обучающийся слой (без внешних библиотек).

Логистическая регрессия: учится на УЖЕ ПРОВЕРЕННЫХ сигналах (фичи -> победа/нет)
и оценивает вероятность успеха для текущих сетапов. Чем больше накоплено
исходов, тем умнее. Пока данных мало — слой молчит (None).
"""
import json, math

FEATURES = ["rsi", "volz", "ret24", "ret6", "dhigh", "dlow", "fund", "lsr", "dir"]
MIN_TRAIN = 40          # минимум проверенных примеров, чтобы доверять модели
EPOCHS = 300
LR = 0.3


def _vec(feat):
    return [float(feat.get(k, 0) or 0) for k in FEATURES]


def _load(conn):
    rows = conn.execute(
        "SELECT features, win FROM signals WHERE graded=1 AND features IS NOT NULL").fetchall()
    X, y = [], []
    for r in rows:
        try:
            f = json.loads(r["features"])
        except Exception:
            continue
        if not f:
            continue
        X.append(_vec(f)); y.append(int(r["win"]))
    return X, y


def train(conn):
    X, y = _load(conn)
    if len(X) < MIN_TRAIN or len(set(y)) < 2:
        return {"ready": False, "n": len(X)}
    m = len(X[0])
    # стандартизация
    means = [sum(col) / len(col) for col in zip(*X)]
    stds = []
    for j in range(m):
        v = sum((X[i][j] - means[j]) ** 2 for i in range(len(X))) / len(X)
        stds.append(math.sqrt(v) or 1.0)
    Xs = [[(row[j] - means[j]) / stds[j] for j in range(m)] for row in X]
    w = [0.0] * m; b = 0.0
    for _ in range(EPOCHS):
        gw = [0.0] * m; gb = 0.0
        for i in range(len(Xs)):
            z = b + sum(w[j] * Xs[i][j] for j in range(m))
            p = 1 / (1 + math.exp(-max(-30, min(30, z))))
            err = p - y[i]
            for j in range(m): gw[j] += err * Xs[i][j]
            gb += err
        n = len(Xs)
        for j in range(m): w[j] -= LR * gw[j] / n
        b -= LR * gb / n
    return {"ready": True, "n": len(X), "w": w, "b": b, "means": means, "stds": stds}


def predict(model, feat):
    if not model or not model.get("ready"):
        return None
    x = _vec(feat); m = len(x)
    z = model["b"] + sum(model["w"][j] * ((x[j] - model["means"][j]) / model["stds"][j]) for j in range(m))
    return 1 / (1 + math.exp(-max(-30, min(30, z))))
