# 本次端到端运行记录

## 1. 起点与环境

- 起点：目录中只有 `跨境电商AI商品推荐与运营分析助手-项目说明.md`，没有代码或数据。
- 环境：Windows PowerShell；Python 3.12.4、Node 24.14.0、npm 11.9.0 可用；Docker 命令不可用；D 盘可用空间约 307 GiB。
- 约束：不使用付费服务，不自动下载完整 OTTO 数据。官方数据规模大，见 [OTTO 官方说明](https://github.com/otto-de/recsys-dataset)。

## 2. 实际操作顺序

| 步骤 | 操作 | 结果与产物 |
| --- | --- | --- |
| 1 | 阅读项目说明，确认 MVP 要覆盖数据、三种基线、API、五个页面和运营助手 | 以合成小样本先完成闭环，真实 OTTO 留可选入口 |
| 2 | 建立 `.venv` 并安装 `requirements.txt`；在 `frontend` 执行 `npm install` | Python 与 React/Vite 依赖安装成功；npm 使用 `registry.npmmirror.com` 镜像完成安装 |
| 3 | 执行 `python -m cbec.pipeline --source demo` | 生成 `data/processed/demo.json`，约 51 KB；160 个合成会话 |
| 4 | 按会话开始时间切分，训练集统计商品行为与共现 | 128 个训练会话、32 个验证会话；12 个商品、672 个训练行为 |
| 5 | 隐藏验证会话后段行为并计算离线指标 | order 目标有 16 个有效验证会话；结果见下表 |
| 6 | 启动 FastAPI 和 Vite | `http://127.0.0.1:8000/api/v1/health` 返回 `ok`；`http://127.0.0.1:5173` 可访问 |
| 7 | 浏览器逐页检查总览、推荐工作台、商品分析、模型评估、运营助手 | 五个页面均显示接口数据；运营问答展示证据与风险 |
| 8 | 执行 `pytest -q` 和 `npm run build` | 3 项测试通过；Vite 生产构建通过 |

## 3. 数据流实际结果

```text
160 个合成 OTTO 格式会话
  → 128 个较早会话用于训练（672 个行为）
  → 32 个较晚会话用于验证（仅前缀进入推荐）
  → 统计 12 个商品的 click/cart/order 次数及加权共现
  → 对 3 种算法分别生成候选与 Top-K
  → 对隐藏后段行为计算 Recall/MRR/NDCG
  → API 返回统一结构
  → React 页面展示与运营助手引用 API 数据
```

训练行为分布：点击 448、加购 160、下单 64；下单/加购事件数比为 0.4。这不是用户转化率。

### order 目标，K=10

| 策略 | 有效会话 | Recall@10 | MRR@10 | NDCG@10 |
| --- | ---: | ---: | ---: | ---: |
| 热门 | 16 | 0.8125 | 0.2937 | 0.4114 |
| 加权共现 | 16 | 1.0000 | 0.4635 | 0.5966 |
| 融合 | 16 | 1.0000 | 0.4755 | 0.6023 |

这些指标来自人为构造的合成数据，只证明算法和评估链路运行正常，不是业务效果或 OTTO 基准成绩。

### 可复核的页面例子

- 验证会话 `900128` 的可见行为：商品 3004 点击、商品 3002 点击与加购。
- `order + hybrid` 推荐前三：商品 3001（0.9625）、3003（0.7511）、3004（0.5122）；每条均返回排名、分数、模型、目标和推荐理由。
- 运营问题“哪些商品适合做组合推荐？”：助手调用商品共现工具，报告商品 2002 与 2001/2003/2004 的加权共现分分别为 37/32/30，并提示共同出现不等于实际一起购买。

## 4. 从零复现

在项目根目录：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m cbec.pipeline --source demo
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn cbec.api:app --host 127.0.0.1 --port 8000
```

另开终端：

```powershell
cd frontend
npm install
npm run dev
```

如 npm 官方仓库访问缓慢，可使用 `npm install --registry=https://registry.npmmirror.com`。打开 `http://127.0.0.1:5173`，或访问 `http://127.0.0.1:8000/docs` 检查接口。

## 5. 当前卡点与边界

1. **真实 OTTO 数据尚未运行。** 官方训练集体量很大，无法仅下载一个很小的官方分片；为遵守本次最小占用要求，没有下载完整包。项目已提供 JSONL 流式读取与 `--limit`，用户已有文件时可直接替换演示数据，见 [数据说明](data/README.md)。
2. **Docker 启动未验证。** 本机没有 Docker 命令；`Dockerfile` 和 Compose 已写好，但本次只验证了本地 Python/Node 路径。
3. **运营助手不是大模型 Agent。** 为保持免费、可验证，它使用规则路由读取真实内部统计，支持五类问题并输出工具调用；自由问答与外部数据接入属于后续迭代。
4. **没有跨境市场属性。** OTTO 匿名行为数据不提供国家、币种、商品标题、利润和库存，本次没有虚构这些字段。
