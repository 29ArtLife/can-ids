"""CAN 报文的窗口特征。

基本单位是一个"窗口"：连续 size 条报文。窗口内的统计量作为一条样本。
标签取窗口内攻击报文占比是否过半。
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def collect_can_ids(df: pd.DataFrame) -> list[str]:
    """收集 can_id 词表。训练集与测试集必须共用同一份词表。"""
    return sorted(df["can_id"].unique().tolist())


def extract_windows(
    df: pd.DataFrame,
    ids: list[str],
    size: int = 1000,
    stride: int | None = None,
) -> tuple[pd.DataFrame, np.ndarray]:
    """按顺序切窗口并提取特征。

    返回 (特征表, 标签数组)。标签 1 表示窗口内攻击报文过半。
    """
    stride = stride or size
    rows: list[dict] = []
    labels: list[int] = []

    for start in range(0, len(df) - size + 1, stride):
        w = df.iloc[start : start + size]

        feat: dict[str, float] = {}
        counts = w["can_id"].value_counts()
        for cid in ids:
            feat[f"n_{cid}"] = float(counts.get(cid, 0))
        feat["uniq_ids"] = float(len(counts))

        dt = w["timestamp"].diff().dropna()
        feat["dt_mean"] = float(dt.mean()) if len(dt) else 0.0
        feat["dt_std"] = float(dt.std()) if len(dt) else 0.0
        feat["dt_min"] = float(dt.min()) if len(dt) else 0.0
        feat["dt_max"] = float(dt.max()) if len(dt) else 0.0
        feat["span"] = float(w["timestamp"].iloc[-1] - w["timestamp"].iloc[0])

        for i in range(8):
            col = w[f"d{i}"]
            feat[f"d{i}_mean"] = float(col.mean())
            feat[f"d{i}_std"] = float(col.std())

        rows.append(feat)
        labels.append(int(w["label"].mean() > 0.5))

    return pd.DataFrame(rows), np.array(labels, dtype=np.int8)
