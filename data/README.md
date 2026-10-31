# 数据使用说明

默认运行 `python -m cbec.pipeline --source demo`，生成 160 个可复现的**合成**会话，保存在 `data/processed/demo.json`。它只用于验证链路，不代表 OTTO 或真实业务表现。

如已有 OTTO `train.jsonl`，可流式读取前 1000 个有效会话，不需将整个文件载入内存：

```powershell
.\.venv\Scripts\python.exe -m cbec.pipeline --source otto --input data/raw/train.jsonl --limit 1000 --output data/processed/otto-small.json
$env:CBEC_DATA_PATH='data/processed/otto-small.json'
```

数据来源：[OTTO 官方数据说明](https://github.com/otto-de/recsys-dataset)、[Kaggle 数据页](https://www.kaggle.com/competitions/otto-recommender-system/data)。官方训练集非常大；本项目不自动下载。若从 Kaggle 获取，请先确认账户权限和可用空间。不要提交原始数据。

该小样本方法按 session 起始时间划分前 80% 训练、后 20% 验证，并把验证会话最后约 40% 行为隐藏作本地标签。它不是官方比赛切分，结果不可与官方榜单比较。前缀抽样也可能导致订单样本稀少；API 会以 `samples=0` 与空指标明确表示。
