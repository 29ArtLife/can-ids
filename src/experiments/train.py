"""随机森林基线：窗口级二分类（正常 / 攻击）。

用法：
    python -m src.io.export          # 先导出 parquet（首次或数据变更后）
    python -m src.experiments.train  # 全量
    python -m src.experiments.train 200000   # 每个数据集随机采样 20 万条

这是打通流程的初步验证，不是正式实验：
    - 按窗口随机划分训练/测试，暂未做时间块隔离
    - 只用了 Car-Hacking 一个数据集
正式实验见 README 中的三类评测协议。
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, f1_score

from src.features.can_features import collect_can_ids, extract_windows
from src.io.export import load_interim

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "results" / "runs.csv"

SEED = 42
WINDOW = 1000


def main(per_set: int | None = None) -> None:
    t0 = time.time()
    print("读取中间数据（parquet）...")
    df = load_interim()
    if per_set:
        # 必须保留时间顺序：攻击是成段注入的，随机采样会把攻击报文
        # 均匀打散，导致每个窗口内攻击占比都低于判定阈值。
        # 这里取每个数据集的中间一段，既控制规模又不破坏时间结构。
        df = (
            df.groupby("attack_type", group_keys=False)
            .apply(lambda g: g.iloc[(len(g) - min(len(g), per_set)) // 2
                                    : (len(g) + min(len(g), per_set)) // 2])
            .reset_index(drop=True)
        )
    print(f"  报文 {len(df):,}｜攻击占比 {df['label'].mean():.1%}｜耗时 {time.time()-t0:.1f}s")

    ids = collect_can_ids(df)
    print(f"  can_id 词表 {len(ids)} 个")

    X, y = extract_windows(df, ids, size=WINDOW)
    print(f"  窗口 {len(X)}｜攻击窗口 {int(y.sum())}（{y.mean():.1%}）")

    rng = np.random.default_rng(SEED)
    idx = rng.permutation(len(X))
    split = int(len(X) * 0.7)
    tr, te = idx[:split], idx[split:]

    clf = RandomForestClassifier(
        n_estimators=200, n_jobs=-1, class_weight="balanced", random_state=SEED
    )
    clf.fit(X.iloc[tr], y[tr])
    pred = clf.predict(X.iloc[te])

    f1 = f1_score(y[te], pred)
    print("\n=== 测试集 ===")
    print(confusion_matrix(y[te], pred))
    print(classification_report(y[te], pred, digits=3, zero_division=0))

    top = pd.Series(clf.feature_importances_, index=X.columns).nlargest(8)
    print("最重要的 8 个特征：")
    for k, v in top.items():
        print(f"  {k:12s} {v:.3f}")

    RUNS.parent.mkdir(parents=True, exist_ok=True)
    if not RUNS.exists():
        RUNS.write_text(
            "timestamp,config,dataset,attack_heldout,model,seed,accuracy,precision,recall,f1,fpr,notes\n",
            encoding="utf-8",
        )
    rep = classification_report(y[te], pred, output_dict=True, zero_division=0)
    tn, fp, fn, tp = confusion_matrix(y[te], pred).ravel()
    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "config": f"window{WINDOW}_per{per_set or 'all'}",
        "dataset": "car-hacking",
        "attack_heldout": "none",
        "model": "rf-200",
        "seed": SEED,
        "accuracy": f"{rep['accuracy']:.4f}",
        "precision": f"{rep['1']['precision']:.4f}",
        "recall": f"{rep['1']['recall']:.4f}",
        "f1": f"{f1:.4f}",
        "fpr": f"{fp / (fp + tn):.4f}",
        "notes": "初步验证：随机划分，未做时间隔离",
    }
    with RUNS.open("a", encoding="utf-8") as f:
        f.write(",".join(str(v) for v in row.values()) + "\n")
    print(f"\n已记录到 results/runs.csv｜总耗时 {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
