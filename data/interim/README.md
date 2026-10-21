# interim

解析后的中间格式，由脚本生成，**不要手工编辑**。

- 各数据集统一为同一套字段：`timestamp, can_id, dlc, data[0..7], label, attack_type`
- 存为 parquet，比 CSV 小且读取快
- 删除后可重新生成
