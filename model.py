import numpy as np

# =========================
# ① Zゾーンスコア
# =========================
def z_zone_score(z):

    z = abs(z)

    # 理想：1.2〜2.2
    if z < 1.0:
        return 0.2
    elif 1.0 <= z < 1.5:
        return 0.8
    elif 1.5 <= z <= 2.2:
        return 1.2  # 最適ゾーン
    elif 2.2 < z <= 3.0:
        return 0.9  # 遅い
    else:
        return 0.4  # 過熱


# =========================
# ② 平均回帰スピード
# =========================
def mean_reversion_speed(spread):

    # 1期間の変化率
    diff = spread.diff().dropna()

    if len(diff) < 5:
        return 0

    speed = -np.mean(diff.tail(5))

    # 正規化
    return max(0, min(1, speed * 50))


# =========================
# ③ 期待値モデル
# =========================
def expected_value(z, speed, risk):

    # 勝率推定
    win_prob = min(0.8, 0.3 + z_zone_score(z))

    # リターン期待値
    reward = z * 10 * speed

    # リスク調整
    risk_penalty = 1 / (1 + risk)

    return win_prob * reward * risk_penalty