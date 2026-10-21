# configs

实验配置。一个 YAML 文件对应一次实验，是复现的唯一依据。

每个配置至少包含：

```yaml
dataset: car-hacking
train_attacks: [DoS, Fuzzy, RPM]
test_attacks: [gear]        # LOAO 时与训练集不重叠
model: rf
seed: 42
window:
  type: count               # count | time
  size: 1000
features: [freq, period, payload]
```

配置文件名同时作为 `results/runs.csv` 中 `config` 列的取值。
