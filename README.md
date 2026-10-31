# CBEC 跨境电商推荐与运营分析助手

这是一个本地可运行的作品集 MVP：从 OTTO 格式会话数据到训练统计、三种推荐基线、离线评估、FastAPI、React 五个页面和证据型运营助手。默认使用明确标注的合成数据，不需要账户、付费服务或大文件下载。

本次实际运行命令、各阶段产物和指标见 [运行记录](RUN_LOG.md)。

## 从零运行（Windows PowerShell）

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m cbec.pipeline --source demo
.\.venv\Scripts\python.exe -m uvicorn cbec.api:app --host 127.0.0.1 --port 8000
```

另开 PowerShell 窗口：

```powershell
cd frontend
npm install
npm run dev
```

浏览器打开 `http://127.0.0.1:5173`。API 文档在 `http://127.0.0.1:8000/docs`，健康检查在 `http://127.0.0.1:8000/api/v1/health`。

已安装 Docker 的机器也可以在根目录运行 `docker compose up --build`。当前开发机器未检测到 Docker，因此此路径尚未实测。

## 五分钟演示

1. 在**总览**查看训练会话、行为次数和数据来源。所有统计来自训练部分。
2. 在**推荐工作台**选择示例会话与目标行为，比较热门、共现、融合策略，查看每个商品的理由。
3. 在**商品分析**查看行为漏斗、日期趋势与关联商品。
4. 在**模型评估**切换 click/cart/order 与 K，比较 Recall、MRR、NDCG 和有效样本数。
5. 在**运营助手**点击五个示例问题，查看结论、证据、行动、风险及实际工具调用。

## 链路和关键假设

```text
OTTO 格式 JSONL / 合成会话
  → 字段校验、排序、行为类型归一
  → 按会话开始时间划分训练/验证
  → 训练集统计商品行为次数和加权共现
  → 验证会话只保留前缀，后续行为作隐藏标签
  → 热门/共现/0.3 热门 + 0.7 共现推荐
  → 按行为目标计算 Recall/MRR/NDCG
  → FastAPI 统一 JSON 接口
  → React 页面及规则驱动运营助手
```

共现权重为点击 1、加购 3、下单 6；会话近期行为以 0.75 的逐步衰减系数计分。当前融合权重为演示用固定值，未从验证集调参。推荐可包含已浏览商品，因为下单目标可能指向曾浏览或加购的商品。行为比值是事件数比值，不是用户转化率。

运营助手是**确定性的工具路由**，不使用付费 LLM。它支持热门商品、商品搭配、行为漏斗、模型效果和日报五类问题，并在其他问题上明确说明数据不足。OTTO 不含商品标题、价格、国家、库存或真实用户身份，因此页面只显示匿名商品 ID。

## 验证

```powershell
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm run build
```

API 统一返回 `{data, meta, error}`；错误使用 404、422、503 与相同结构。可选 OTTO 小样本处理见 [数据说明](data/README.md)。

## 当前限制与下一步

- 默认指标来自合成数据，只证明链路可运行，不能用于业务效果结论。
- OTTO 小样本是本地自定义验证，不等同官方切分；完整训练集与深度模型均未运行。
- 没有真实商品属性及线上反馈，搭配建议需人工核对并通过 A/B 测试。
- Docker 配置已提供，但当前机器未安装 Docker，需在有 Docker 的环境验证。
- 下一步可以用授权取得的真实数据小样本重跑，随后增加排序模型与多市场商品信息。

## 公开版本说明

- 仓库不包含原始 OTTO 数据、用户数据、已生成的数据文件、虚拟环境、node_modules 或个人配置。
- 第一次运行需执行 `python -m cbec.pipeline --source demo` 生成可复现的合成数据。
- 演示指标仅证明端到端链路可运行，不能声称真实电商业务提升。
- 提供的 Docker 配置尚未在 Docker 环境实测；本地 Python/Node 路径与 Docker 验证分开记录。

## 作品分类

本项目使用 GitHub Topics 标记用途。同系列公开项目：

| 类别 | 项目 |
| --- | --- |
| 图像与创作 | [拾光修图](https://github.com/JiaDongZou/photo-studio) |
| 英语与学习 | [句间英语播放器](https://github.com/JiaDongZou/english-study-player) |
| AI 与电商分析 | [CBEC 推荐与运营分析](https://github.com/JiaDongZou/cbec-recommendation-assistant) |
| 生活与微信小程序 | [我的私人食谱](https://github.com/JiaDongZou/recipe-miniprogram) |
