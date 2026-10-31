"""Transparent baselines and offline evaluation for the local demo."""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

WEIGHTS = {"click": 1, "cart": 3, "order": 6}
MODELS = ("popularity", "cooccurrence", "hybrid")
TARGETS = ("click", "cart", "order")


class Store:
    def __init__(self, path: Path):
        self.path = path
        self.data = json.loads(path.read_text(encoding="utf-8"))
        self.train = self.data["train"]
        self.visible = self.data["validation"]
        self.sessions = {r["session"]: r["events"] for r in self.train + self.visible}
        self.stats = defaultdict(Counter)
        self.pairs = defaultdict(Counter)
        self.pop = {t: Counter() for t in TARGETS}
        for row in self.train:
            item_weights = defaultdict(float)
            for event in row["events"]:
                aid, kind = event["aid"], event["type"]
                self.stats[aid][kind] += 1
                self.pop[kind][aid] += 1
                item_weights[aid] += WEIGHTS[kind]
            for aid, value in item_weights.items():
                for other, other_value in item_weights.items():
                    if aid != other:
                        self.pairs[aid][other] += min(value, other_value)
        self.metrics = self.evaluate()

    def recommend(self, session: int, k: int = 10, target: str = "order", model: str = "hybrid") -> list[dict]:
        if session not in self.sessions:
            raise KeyError(session)
        if target not in TARGETS or model not in MODELS:
            raise ValueError("invalid target or model")
        events = self.sessions[session]
        popularity = self.pop[target]
        max_pop = max(popularity.values(), default=1)
        related = defaultdict(float)
        for index, event in enumerate(events):
            recency = 0.75 ** (len(events) - index - 1)
            for aid, count in self.pairs[event["aid"]].items():
                related[aid] += count * WEIGHTS[event["type"]] * recency
        max_related = max(related.values(), default=1)
        candidates = set(popularity) | set(related)
        scored = []
        for aid in candidates:
            p = popularity[aid] / max_pop
            c = related[aid] / max_related
            score = p if model == "popularity" else c if model == "cooccurrence" else 0.3 * p + 0.7 * c
            if score <= 0:
                continue
            reasons = []
            if p > 0:
                reasons.append(f"训练集 {target} 行为 {popularity[aid]} 次")
            if c > 0:
                reasons.append("与会话近期商品共同出现")
            scored.append((score, aid, reasons))
        scored.sort(key=lambda row: (-row[0], row[1]))
        return [{"item_id": aid, "score": round(score, 4), "rank": rank, "reasons": reasons,
                 "model": model, "target": target} for rank, (score, aid, reasons) in enumerate(scored[:k], 1)]

    def evaluate(self) -> list[dict]:
        labels = {row["session"]: row["events"] for row in self.data["labels"]}
        output = []
        for model in MODELS:
            for target in TARGETS:
                for k in (5, 10, 20):
                    totals = Counter()
                    samples = 0
                    for row in self.visible:
                        truth = {e["aid"] for e in labels[row["session"]] if e["type"] == target}
                        if not truth:
                            continue
                        ranked = [r["item_id"] for r in self.recommend(row["session"], k, target, model)]
                        hits = [i + 1 for i, aid in enumerate(ranked) if aid in truth]
                        totals["recall"] += len(hits) / len(truth)
                        totals["mrr"] += 1 / min(hits) if hits else 0
                        dcg = sum(1 / math.log2(rank + 1) for rank in hits)
                        ideal = sum(1 / math.log2(rank + 1) for rank in range(1, min(len(truth), k) + 1))
                        totals["ndcg"] += dcg / ideal if ideal else 0
                        samples += 1
                    output.append({"model": model, "target": target, "k": k, "samples": samples,
                                   **{metric: round(totals[metric] / samples, 4) if samples else None
                                      for metric in ("recall", "mrr", "ndcg")}})
        return output

    def overview(self) -> dict:
        all_events = [e for row in self.train for e in row["events"]]
        totals = Counter(e["type"] for e in all_events)
        best = max((r for r in self.metrics if r["target"] == "order" and r["k"] == 10 and r["ndcg"] is not None),
                   key=lambda r: r["ndcg"], default=None)
        return {"source": self.data["source"], "train_sessions": len(self.train),
                "validation_sessions": len(self.visible), "items": len(self.stats), "events": len(all_events),
                "clicks": totals["click"], "carts": totals["cart"], "orders": totals["order"],
                "cart_to_order_ratio": round(totals["order"] / totals["cart"], 4) if totals["cart"] else None,
                "best_order_ndcg_at_10": best, "time_start": min(e["ts"] for e in all_events),
                "time_end": max(e["ts"] for e in all_events), "skipped_rows": self.data["skipped_rows"]}

    def item_stats(self, aid: int) -> dict:
        if aid not in self.stats:
            raise KeyError(aid)
        counts = self.stats[aid]
        days = defaultdict(Counter)
        for row in self.train:
            for event in row["events"]:
                if event["aid"] == aid:
                    day = datetime.fromtimestamp(event["ts"] / 1000, timezone.utc).date().isoformat()
                    days[day][event["type"]] += 1
        return {"item_id": aid, "clicks": counts["click"], "carts": counts["cart"], "orders": counts["order"],
                "click_to_cart_ratio": round(counts["cart"] / counts["click"], 4) if counts["click"] else None,
                "cart_to_order_ratio": round(counts["order"] / counts["cart"], 4) if counts["cart"] else None,
                "trend": [{"date": day, **{t: value[t] for t in TARGETS}} for day, value in sorted(days.items())]}

    def top_items(self, metric: str = "order", limit: int = 10) -> list[dict]:
        if metric not in TARGETS:
            raise ValueError(metric)
        return [{"item_id": aid, "count": count} for aid, count in self.pop[metric].most_common(limit)]

    def related(self, aid: int, limit: int = 10) -> list[dict]:
        if aid not in self.stats:
            raise KeyError(aid)
        return [{"item_id": other, "cooccurrence_score": round(score, 2)}
                for other, score in self.pairs[aid].most_common(limit)]

    def report(self) -> dict:
        top = self.top_items("order", 5)
        best = max((r for r in self.metrics if r["target"] == "order" and r["k"] == 10 and r["ndcg"] is not None),
                   key=lambda r: r["ndcg"], default=None)
        return {"answer": "训练数据中的下单行为与离线推荐效果摘要。",
                "evidence": [f"商品 {r['item_id']}：{r['count']} 次下单行为" for r in top] +
                            ([f"{best['model']} 的 order NDCG@10={best['ndcg']}，样本 {best['samples']}"] if best else []),
                "actions": ["先检查高频商品库存与搭配展示，再进行受控线上实验。"],
                "risks": ["此为匿名会话数据；事件比值不等于真实用户转化率。", "离线指标不能证明销售增量。"],
                "tool_calls": [{"tool": "get_top_items", "arguments": {"metric": "order", "limit": 5}},
                               {"tool": "compare_recommendation_models", "arguments": {"target": "order", "k": 10}}]}

    def answer(self, question: str) -> dict:
        q = question.lower().strip()
        if not q:
            raise ValueError("question is empty")
        if any(word in q for word in ("组合", "搭配", "共现", "related", "bundle")):
            aid = self.top_items("order", 1)[0]["item_id"]
            related = self.related(aid, 3)
            return {"answer": f"可先检查商品 {aid} 的共同出现商品，作为搭配候选。",
                    "evidence": [f"{aid} 与 {r['item_id']} 的加权共现分 {r['cooccurrence_score']}" for r in related],
                    "actions": ["人工核对商品是否互补，再做小流量组合展示。"],
                    "risks": ["共同出现不代表因果或实际一起购买。"],
                    "tool_calls": [{"tool": "get_item_cooccurrence", "arguments": {"item_id": aid, "limit": 3}}]}
        if any(word in q for word in ("推荐", "模型", "效果", "评估", "ndcg", "recall")):
            rows = [r for r in self.metrics if r["target"] == "order" and r["k"] == 10]
            return {"answer": "以下是 order 目标的离线模型对比。",
                    "evidence": [f"{r['model']}: NDCG@10={r['ndcg']}, Recall@10={r['recall']}, 样本={r['samples']}" for r in rows],
                    "actions": ["选择离线表现较好的策略进入线上 A/B 测试。"],
                    "risks": ["小样本或合成数据指标不可推广到真实业务。"],
                    "tool_calls": [{"tool": "compare_recommendation_models", "arguments": {"target": "order", "k": 10}}]}
        if any(word in q for word in ("加购", "转化", "漏斗", "cart")):
            data = self.overview()
            return {"answer": "训练集行为漏斗概览。",
                    "evidence": [f"点击 {data['clicks']}、加购 {data['carts']}、下单 {data['orders']} 次行为", f"下单行为数/加购行为数={data['cart_to_order_ratio']}"],
                    "actions": ["按商品进一步检查加购与下单行为差异。"],
                    "risks": ["该比值基于事件数，不是用户转化率。"],
                    "tool_calls": [{"tool": "get_overview", "arguments": {}}]}
        if any(word in q for word in ("热门", "排行", "top", "热销")):
            top = self.top_items("order", 5)
            return {"answer": "按训练集下单行为次数排序的热门商品。",
                    "evidence": [f"商品 {r['item_id']}：{r['count']} 次" for r in top],
                    "actions": ["核对库存、毛利和活动适配度。"],
                    "risks": ["没有价格、库存、国家与利润数据。"],
                    "tool_calls": [{"tool": "get_top_items", "arguments": {"metric": "order", "limit": 5}}]}
        if any(word in q for word in ("日报", "周报", "报告", "report")):
            return self.report()
        return {"answer": "当前数据不足以直接回答这个问题。可询问热门商品、组合推荐、行为漏斗、模型效果或运营报告。",
                "evidence": [], "actions": ["补充商品 ID 或选择支持的分析主题。"],
                "risks": ["未进行自由生成；没有编造外部业务指标。"], "tool_calls": []}
