"""把原始数据解析后落盘为 parquet，供各实验复用。

用法：
    python -m src.io.export            # 全量
    python -m src.io.export 200000     # 每个文件只处理前 20 万行（调试用）

输出：data/interim/<数据集名>.parquet + _meta.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from src.io.loaders import ATTACK_FILES, load_attack, load_normal

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"


def export_all(max_rows: int | None = None) -> dict:
    """解析全部数据集并写入 parquet，返回元信息。"""
    INTERIM.mkdir(parents=True, exist_ok=True)

    sets: dict[str, pd.DataFrame] = {"Normal": load_normal(RAW, max_rows)}
    for name in ATTACK_FILES:
        sets[name] = load_attack(RAW, name, max_rows)

    meta: dict[str, dict] = {}
    for name, df in sets.items():
        path = INTERIM / f"{name}.parquet"
        df.to_parquet(path, index=False)
        meta[name] = {
            "file": path.name,
            "rows": len(df),
            "attack_rows": int(df["label"].sum()),
            "attack_ratio": round(float(df["label"].mean()), 4),
            "can_ids": int(df["can_id"].nunique()),
            "size_mb": round(path.stat().st_size / 1048576, 1),
        }
        print(f"  {name:8s} {len(df):>9,} 行 → {path.name}  {meta[name]['size_mb']} MB")

    (INTERIM / "_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return meta


def load_interim(names: list[str] | None = None) -> pd.DataFrame:
    """读取已导出的中间数据。默认读全部并拼接。"""
    meta_path = INTERIM / "_meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(
            f"{meta_path} 不存在，请先运行：python -m src.io.export"
        )
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    names = names or list(meta)
    return pd.concat(
        [pd.read_parquet(INTERIM / meta[n]["file"]) for n in names],
        ignore_index=True,
    )


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else None
    print(f"导出到 {INTERIM}（{'全量' if n is None else f'每文件前 {n:,} 行'}）")
    m = export_all(n)
    total = sum(v["rows"] for v in m.values())
    print(f"完成：{len(m)} 个文件，共 {total:,} 条报文")
