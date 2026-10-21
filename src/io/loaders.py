"""数据集解析器：把原始文件转成统一结构。

统一字段：
    timestamp   记录时间（秒，float）
    can_id      CAN 标识符（小写十六进制字符串）
    dlc         数据长度码
    d0..d7      数据字节（不足补 0）
    label       0=正常，1=攻击
    attack_type DoS / Fuzzy / RPM / gear / Normal
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

CAN_COLS = ["timestamp", "can_id", "dlc"] + [f"d{i}" for i in range(8)]
BASE_COLS = CAN_COLS + ["label", "attack_type"]

ATTACK_FILES = {
    "DoS": "DoS_dataset.csv",
    "Fuzzy": "Fuzzy_dataset.csv",
    "RPM": "RPM_dataset.csv",
    "gear": "gear_dataset.csv",
}

_ATTACK_COLS = CAN_COLS + ["flag"]
_NORMAL_RE = re.compile(
    r"Timestamp:\s*([\d.]+)\s+ID:\s*(\w+)\s+\S+\s+DLC:\s*(\d+)\s+([0-9a-fA-F ]+)"
)


def load_attack(raw_dir: Path | str, attack: str, max_rows: int | None = None) -> pd.DataFrame:
    """读取一个攻击数据集（CSV，无表头，末列为 R/T 标记）。"""
    path = Path(raw_dir) / ATTACK_FILES[attack]
    df = pd.read_csv(path, header=None, names=_ATTACK_COLS, nrows=max_rows)
    df["can_id"] = df["can_id"].astype(str).str.lower()
    df["label"] = (df.pop("flag").astype(str).str.strip() == "T").astype("int8")
    df["attack_type"] = attack
    return df[BASE_COLS]


def load_normal(raw_dir: Path | str, max_rows: int | None = None) -> pd.DataFrame:
    """读取正常行驶数据（纯文本，格式与 CSV 不同，逐行解析）。"""
    path = Path(raw_dir) / "normal_run_data" / "normal_run_data.txt"
    rows: list[list] = []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if max_rows is not None and len(rows) >= max_rows:
                break
            m = _NORMAL_RE.match(line)
            if not m:
                continue
            ts, cid, dlc, data = m.groups()
            payload = [int(b, 16) for b in data.split()][:8]
            rows.append([float(ts), cid.lower(), int(dlc)] + payload + [0] * (8 - len(payload)))
    df = pd.DataFrame(rows, columns=CAN_COLS)
    df["label"] = 0
    df["attack_type"] = "Normal"
    return df[BASE_COLS]


def load_all(raw_dir: Path | str, max_rows: int | None = None) -> pd.DataFrame:
    """拼接正常数据与全部攻击数据。"""
    parts = [load_normal(raw_dir, max_rows)]
    parts += [load_attack(raw_dir, a, max_rows) for a in ATTACK_FILES]
    return pd.concat(parts, ignore_index=True)


if __name__ == "__main__":
    raw = Path(__file__).resolve().parents[2] / "data" / "raw"

    normal = load_normal(raw, max_rows=500)
    assert len(normal) > 0, "正常数据解析失败"
    assert normal["label"].sum() == 0
    assert normal["can_id"].str.fullmatch(r"[0-9a-f]{1,8}").all()

    # 注意：数据集按时间顺序存储，开头一段全是正常报文；
    # 读太少行会看不到攻击样本，所以自检取 5 万行。
    for attack in ATTACK_FILES:
        df = load_attack(raw, attack, max_rows=50000)
        assert len(df) > 0, f"{attack} 未读到数据"
        assert set(df["label"].unique()) <= {0, 1}
        assert df["label"].sum() > 0, f"{attack} 中没有攻击样本"
        assert df["attack_type"].eq(attack).all()

    print("正常样本", len(normal), "| can_id 数", normal["can_id"].nunique())
    print("前 3 行：")
    print(normal.head(3).to_string(index=False))
    print("自检通过")
