"""Small, deterministic OTTO-format dataset preparation; no large file is downloaded."""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

TYPES = {"click": "click", "clicks": "click", "cart": "cart", "carts": "cart", "order": "order", "orders": "order"}


def normalize(row: dict) -> dict:
    sid = int(row["session"])
    events = []
    for raw in row["events"]:
        kind = TYPES[raw["type"]]
        events.append({"aid": int(raw["aid"]), "ts": int(raw["ts"]), "type": kind})
    events.sort(key=lambda e: e["ts"])
    if len(events) < 2:
        raise ValueError("session needs at least two events")
    return {"session": sid, "events": events}


def make_demo(count: int = 160) -> list[dict]:
    rng = random.Random(42)
    groups = [[1001, 1002, 1003, 1004], [2001, 2002, 2003, 2004], [3001, 3002, 3003, 3004]]
    rows = []
    for i in range(count):
        group = groups[i % 3]
        base = 1661200000000 + i * 3600000
        chosen = rng.sample(group, 3)
        events = [
            {"aid": chosen[0], "ts": base, "type": "click"},
            {"aid": chosen[1], "ts": base + 60000, "type": "click"},
            {"aid": chosen[1], "ts": base + 120000, "type": "cart"},
            {"aid": chosen[2], "ts": base + 180000, "type": "click"},
        ]
        if i % 4 == 0:
            events.append({"aid": chosen[2], "ts": base + 240000, "type": "cart"})
        events.append({"aid": chosen[1] if i % 3 == 0 else chosen[2], "ts": base + 300000, "type": "order" if i % 2 == 0 else "click"})
        rows.append({"session": 900000 + i, "events": events})
    return rows


def read_jsonl(path: Path, limit: int) -> tuple[list[dict], int]:
    rows, skipped = [], 0
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if len(rows) >= limit:
                break
            try:
                rows.append(normalize(json.loads(line)))
            except (ValueError, KeyError, TypeError, json.JSONDecodeError):
                skipped += 1
    if not rows:
        raise ValueError("no valid sessions found")
    return rows, skipped


def prepare(rows: list[dict], source: str, skipped: int = 0) -> dict:
    rows = sorted(rows, key=lambda r: (r["events"][0]["ts"], r["session"]))
    cut = max(1, int(len(rows) * 0.8))
    if cut == len(rows):
        cut -= 1
    train, validation = rows[:cut], rows[cut:]
    # Only visible validation prefixes are exposed to the app. Held-out events stay in evaluation labels.
    visible, labels = [], []
    for row in validation:
        events = row["events"]
        split = max(1, int(len(events) * 0.6))
        visible.append({"session": row["session"], "events": events[:split]})
        labels.append({"session": row["session"], "events": events[split:]})
    return {"source": source, "train": train, "validation": visible, "labels": labels,
            "skipped_rows": skipped, "split": "first 80% of sessions by start time for training; last 20% for validation, with final 40% of each validation session hidden"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["demo", "otto"], default="demo")
    parser.add_argument("--input", type=Path, help="OTTO train.jsonl path; required for --source otto")
    parser.add_argument("--limit", type=int, default=160)
    parser.add_argument("--output", type=Path, default=Path("data/processed/demo.json"))
    args = parser.parse_args()
    if args.limit < 10 or args.limit > 10000:
        parser.error("--limit must be between 10 and 10000")
    if args.source == "otto":
        if not args.input:
            parser.error("--input is required for OTTO")
        rows, skipped = read_jsonl(args.input, args.limit)
        source = "OTTO sample"
    else:
        rows, skipped, source = make_demo(args.limit), 0, "synthetic demo"
    prepared = prepare(rows, source, skipped)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(prepared, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "source": source, "train_sessions": len(prepared["train"]),
                      "validation_sessions": len(prepared["validation"]), "skipped_rows": skipped}, ensure_ascii=False))


if __name__ == "__main__":
    main()
