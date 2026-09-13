import json
from datetime import datetime, timezone
from pathlib import Path

from collect import collect
from sources import Source

NOW = datetime(2026, 9, 14, 0, 0, tzinfo=timezone.utc)
YT = Source("Y", "youtube", "UC1", "ja", "AI活用")
RSS = Source("R", "rss", "https://r/feed", "ja", "個人開発")
BAD = Source("B", "rss", "https://bad/feed", "ja", "その他")


def item(i, typ, src):
    return {"id": i, "source": src, "type": typ, "title": "t " + i, "url": "https://u/" + i,
            "published": NOW.isoformat(), "lang": "ja", "topic": "x", "summary": "s"}


def fake_fetch(source):
    if source.name == "Y":
        return [item("yt:v1", "youtube", "Y"), item("yt:v2", "youtube", "Y")]
    if source.name == "R":
        return [item("https://r/1", "rss", "R")]
    raise TimeoutError("timeout")


def fake_transcript(video_id, work_dir):
    if video_id == "v1":
        return {"text": "字幕の本文", "lang": "ja", "duration_sec": 600}
    return None


def test_collect_writes_inbox_and_state(tmp_path):
    inbox, state = tmp_path / "inbox", tmp_path / "state"
    result = collect([YT, RSS, BAD], inbox, state, fetch=fake_fetch, get_transcript=fake_transcript, now=NOW, log=lambda *_: None)
    assert result == {"new": 3, "failed": ["B"]}
    items = json.loads((inbox / "items.json").read_text(encoding="utf-8"))
    by_id = {it["id"]: it for it in items}
    assert by_id["yt:v1"]["transcript_file"] == "transcripts/v1.txt"
    assert by_id["yt:v1"]["transcript_lang"] == "ja" and by_id["yt:v1"]["duration_sec"] == 600
    assert (inbox / "transcripts" / "v1.txt").read_text(encoding="utf-8") == "字幕の本文"
    assert by_id["yt:v2"]["transcript_file"] is None
    assert by_id["https://r/1"]["transcript_file"] is None
    assert all(it["collected_at"] == NOW.isoformat() for it in items)
    seen = json.loads((state / "seen.json").read_text(encoding="utf-8"))
    assert set(seen["ids"]) == {"yt:v1", "yt:v2", "https://r/1"}
    failures = json.loads((state / "failures.json").read_text(encoding="utf-8"))
    assert failures["B"]["count"] == 1


def test_second_collect_adds_nothing_and_keeps_inbox(tmp_path):
    inbox, state = tmp_path / "inbox", tmp_path / "state"
    kw = dict(fetch=fake_fetch, get_transcript=fake_transcript, now=NOW, log=lambda *_: None)
    collect([YT, RSS], inbox, state, **kw)
    result = collect([YT, RSS], inbox, state, **kw)
    assert result["new"] == 0
    assert len(json.loads((inbox / "items.json").read_text(encoding="utf-8"))) == 3


def test_transcript_failure_does_not_drop_item(tmp_path):
    def boom(video_id, work_dir):
        raise RuntimeError("yt-dlp died")
    result = collect([YT], tmp_path / "inbox", tmp_path / "state", fetch=fake_fetch, get_transcript=boom, now=NOW, log=lambda *_: None)
    assert result["new"] == 2
    items = json.loads((tmp_path / "inbox" / "items.json").read_text(encoding="utf-8"))
    assert all(it["transcript_file"] is None for it in items)
