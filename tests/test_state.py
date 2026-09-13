from datetime import datetime, timedelta, timezone

from state import load_json, record_result, save_json, split_new

NOW = datetime(2026, 9, 14, 0, 0, tzinfo=timezone.utc)


def item(i, hours_ago):
    return {"id": i, "published": (NOW - timedelta(hours=hours_ago)).isoformat()}


def test_first_run_takes_only_last_24h_and_marks_all_seen():
    items = [item("a", 1), item("b", 23), item("c", 25), item("d", 200)]
    new, seen = split_new(items, {"ids": [], "sources": []}, "S", NOW)
    assert [x["id"] for x in new] == ["a", "b"]
    assert set(seen["ids"]) == {"a", "b", "c", "d"}
    assert seen["sources"] == ["S"]


def test_second_run_takes_everything_unseen_regardless_of_date():
    seen = {"ids": ["a"], "sources": ["S"]}
    new, seen2 = split_new([item("a", 1), item("e", 300)], seen, "S", NOW)
    assert [x["id"] for x in new] == ["e"]
    assert set(seen2["ids"]) == {"a", "e"}


def test_json_roundtrip(tmp_path):
    p = tmp_path / "x" / "seen.json"
    assert load_json(p, {"ids": []}) == {"ids": []}
    save_json(p, {"ids": ["日本語"]})
    assert load_json(p, None) == {"ids": ["日本語"]}


def test_record_result_counts_consecutive_failures():
    f = record_result({}, "S", "timeout", NOW)
    f = record_result(f, "S", "timeout", NOW)
    assert f["S"]["count"] == 2 and f["S"]["last_error"] == "timeout"
    f = record_result(f, "S", None, NOW)
    assert "S" not in f
