import json

from fastapi.testclient import TestClient

from cbec import api
from cbec.engine import Store
from cbec.pipeline import make_demo, prepare, read_jsonl


def test_otto_jsonl_normalization(tmp_path):
    path = tmp_path / "train.jsonl"
    path.write_text('\n'.join([
        json.dumps({"session": 1, "events": [{"aid": 11, "ts": 2, "type": "orders"}, {"aid": 12, "ts": 1, "type": "clicks"}]}),
        "not json",
        json.dumps({"session": 2, "events": [{"aid": 11, "ts": 3, "type": "carts"}, {"aid": 13, "ts": 4, "type": "clicks"}]}),
    ]) + '\n', encoding="utf-8")
    rows, skipped = read_jsonl(path, 10)
    assert skipped == 1
    assert [e["type"] for e in rows[0]["events"]] == ["click", "order"]
    assert rows[0]["events"][0]["ts"] == 1


def test_time_split_and_hidden_labels(tmp_path):
    prepared = prepare(make_demo(40), "synthetic demo")
    train_end = max(e["ts"] for row in prepared["train"] for e in row["events"])
    validation_start = min(e["ts"] for row in prepared["validation"] for e in row["events"])
    assert train_end < validation_start
    for visible, label in zip(prepared["validation"], prepared["labels"]):
        assert visible["session"] == label["session"]
        assert max(e["ts"] for e in visible["events"]) < min(e["ts"] for e in label["events"])
    path = tmp_path / "demo.json"
    path.write_text(json.dumps(prepared), encoding="utf-8")
    store = Store(path)
    assert store.evaluate()
    assert all(row["samples"] > 0 for row in store.metrics if row["target"] == "click")


def test_api_end_to_end(tmp_path, monkeypatch):
    path = tmp_path / "demo.json"
    path.write_text(json.dumps(prepare(make_demo(60), "synthetic demo")), encoding="utf-8")
    monkeypatch.setattr(api, "DATA_PATH", path)
    monkeypatch.setattr(api, "store", None)
    client = TestClient(api.app)
    assert client.get("/api/v1/health").json()["data"]["data_ready"]
    sid = client.get("/api/v1/sessions").json()["data"][0]["session_id"]
    session = client.get(f"/api/v1/sessions/{sid}").json()["data"]
    assert session["events"]
    rec = client.get(f"/api/v1/recommendations/{sid}?target=order&model=hybrid").json()["data"]["results"]
    assert rec and rec[0]["rank"] == 1 and rec[0]["reasons"]
    item = rec[0]["item_id"]
    assert client.get(f"/api/v1/items/{item}/stats").status_code == 200
    assert client.get("/api/v1/metrics/evaluation").json()["data"]["results"]
    for question in ("热门商品", "组合推荐", "加购转化", "推荐效果", "运营日报"):
        result = client.post("/api/v1/agent/chat", json={"question": question}).json()["data"]
        assert result["answer"] and result["evidence"] and result["tool_calls"]
    assert client.get("/api/v1/recommendations/0").status_code == 404
    bad = client.get(f"/api/v1/recommendations/{sid}?k=0")
    assert bad.status_code == 422 and bad.json()["error"]["code"] == 422
