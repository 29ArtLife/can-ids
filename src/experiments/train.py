"""随机森林基线：窗口级二分类（正常 / 攻击）。

用法：
    python -m src.experiments.train [每个文件读取行数]

这是打通流程的初步验证，不是正式实验：
    - 按窗口随机划分训练/测试，暂未做时间块隔离
    - 只用了 Car-Hacking 一个数据集
正式实验见 README 中的三类评测协议。
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, f1_score

from src.features.can_features import collect_can_ids, extract_windows
from src.io.loaders import ATTACK_FILES, load_attack, load_normal

RAW = Path(__file__).resolve().parents[2] / "data" / "raw"
RUNS = Path(__file__).resolve().parents[2] / "results" / "runs.csv"

SEED = 42
WINDOW = 1000


def main(max_rows: int = 200_000) -> None:
    print(f"读取数据（每个文件 {max_rows} 行）...")
    parts = [load_normal(RAW, max_rows)]
    parts += [load_attack(RAW, a, max_rows) for a in ATTACK_FILES]
    df = pd.concat(parts, ignore_index=True)
    print(f"  总报文 {len(df):,}｜攻击占比 {df['label'].mean():.1%}")

    ids = collect_can_ids(df)
    print(f"  can_id 词表 {len(ids)} 个")

    X, y = extract_windows(df, ids, size=WINDOW)
    print(f"窗口数 {len(X)}｜攻击窗口 {y.sum()}（{y.mean():.1%}）")

    rng = np.random.default_rng(SEED)
    idx = rng.permutation(len(X))
    split = int(len(X) * 0.7)
    tr, te = idx[:split], idx[split:]

    clf = RandomForestClassifier(
        n_estimators=200, max_depth=None, n_jobs=-1,
        class_weight="balanced", random_state=SEED,
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

    # 记录实验（runs.csv 的约定：每次实验追加一行）
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
        "config": f"window{WINDOW}_rows{max_rows}",
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
    print(f"\n已记录到 {RUNS.relative_to(RUNS.parents[1])}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 200_000)
