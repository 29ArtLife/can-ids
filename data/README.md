# 数据目录说明

原始数据不纳入 Git 版本管理（体积大、有独立使用条款）。本文件说明数据来源、获取方式与字段定义。

## 目录约定

| 目录 | 内容 | 是否入库 |
|---|---|---|
| `raw/` | 官方原始文件，解压后原样保存 | 否 |
| `interim/` | 解析后的统一格式（parquet） | 否 |
| `processed/` | 切好窗口的训练/测试集 | 否 |

## Car-Hacking Dataset

**来源**：韩国高丽大学 HCRL 实验室（Cyber Security & Privacy Lab）
**主页**：https://ocslab.hksecurity.net/Datasets/car-hacking-dataset
**下载**：官方提供 Dropbox 文件夹，完整数据集约 953 MB
**本地文件名**：`raw/car-hacking-full.zip`

### 获取方式

```bash
bash scripts/download_data.sh
```

### 字段定义

除正常行驶数据外，各文件包含以下列：

| 列名 | 说明 |
|---|---|
| Timestamp | 记录时间，单位秒 |
| CAN ID | 报文标识符，十六进制（如 `043f`） |
| DLC | 数据长度码，0–8 |
| DATA[0]–DATA[7] | 数据字节 |
| Flag | `T` 表示注入的攻击报文，`R` 表示正常报文 |

正常数据文件（`normal_run_data.txt`）不含 Flag 列，全部为正常报文。

### 攻击类型

| 类型 | 特征 |
|---|---|
| DoS | 以最高优先级 CAN ID `0000`、每 0.3 ms 注入一条 |
| Fuzzy | 随机 CAN ID 与随机数据、每 0.5 ms 注入一条 |
| Spoofing the drive gear | 伪造挡位相关 CAN ID，每 1 ms 一条 |
| Spoofing the RPM gauge | 伪造转速相关 CAN ID，每 1 ms 一条 |
| Normal | 无注入的正常行驶数据 |

每个攻击文件含 300 次注入，每次持续 3–5 秒，总时长约 30–40 分钟。

### 数据布局注意（实测）

数据集**按时间顺序存储**，每个攻击文件的开头一段全是正常报文——实测前 2000 行里一条攻击都没有。攻击段分散在中后部。

按前 20 万行统计的标签比例：

| 文件 | 攻击报文占比 |
|---|---|
| DoS_dataset.csv | 24.3% |
| gear_dataset.csv | 18.5% |
| RPM_dataset.csv | 18.5% |
| Fuzzy_dataset.csv | 14.7% |

由此带来两个必须注意的问题：

1. **不能按行号简单切分训练/测试集**。若直接取前 N 行做训练，训练集可能一条攻击都没有。
2. **按时间块切分时要检查区块内标签分布**，并保证同一时间段不跨训练集与测试集。

解析器自检因此读取 5 万行（而非前 2000 行）来确认攻击样本存在。

### 引用

```bibtex
@inproceedings{seo2018gids,
  title={GIDS: GAN based Intrusion Detection System for In-Vehicle Network},
  author={Seo, Eunbi and Song, Hyun Min and Kim, Huy Kang},
  booktitle={2018 16th Annual Conference on Privacy, Security and Trust (PST)},
  year={2018}
}
```

## 其他数据集

以下数据集在后续阶段接入，获取方式另行补充：

| 数据集 | 状态 |
|---|---|
| ROAD (ORNL) | 待获取 |
| CAN-Train-and-Test | 待获取 |
| VeReMi / VeReMi Extension | 待获取 |

## 注意

- 数据集仅供学术研究使用，不得用于商业用途
- 不要把原始数据提交到本仓库
- 解析后的中间文件同样不入库，由脚本生成
