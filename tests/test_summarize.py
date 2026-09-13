from pathlib import Path

from summarize import build_materials, build_prompt, estimate_tokens, failures_section, fallback_digest


def mk(i, **kw):
    base = {"id": i, "source": "S", "type": "rss", "title": "題 " + i, "url": "https://u/" + i,
            "published": "2026-09-13T08:00:00+00:00", "lang": "ja", "topic": "AI活用", "summary": "冒頭",
            "transcript_file": None, "transcript_lang": None, "duration_sec": None}
    base.update(kw)
    return base


def test_estimate_tokens():
    assert estimate_tokens("あ" * 100, "ja") == 50
    assert estimate_tokens("a" * 100, "en") == 25


def test_build_materials_includes_transcript_and_marks_missing(tmp_path):
    (tmp_path / "transcripts").mkdir()
    (tmp_path / "transcripts" / "v1.txt").write_text("字幕本文", encoding="utf-8")
    items = [mk("yt:v1", type="youtube", transcript_file="transcripts/v1.txt", transcript_lang="ja", duration_sec=1080),
             mk("yt:v2", type="youtube", lang="en")]
    m = build_materials(items, tmp_path)
    assert "=== 資料 1 ===" in m and "=== 資料 2 ===" in m
    assert "種別: 動画 18 分（字幕 ja）" in m and "字幕本文" in m
    assert "種別: 動画（概要欄のみ）" in m
    assert "言語: en" in m


def test_build_materials_truncates_long_text(tmp_path):
    (tmp_path / "transcripts").mkdir()
    (tmp_path / "transcripts" / "v1.txt").write_text("あ" * 100, encoding="utf-8")
    items = [mk("yt:v1", type="youtube", transcript_file="transcripts/v1.txt", transcript_lang="ja")]
    m = build_materials(items, tmp_path, max_chars=10)
    assert "あ" * 10 + "…（以下略）" in m and "あ" * 11 not in m


def test_build_prompt_fills_placeholders():
    p = build_prompt("# {DATE}\n{MATERIALS}", "MAT", "2026-09-14")
    assert p == "# 2026-09-14\nMAT"


def test_failures_section():
    s = failures_section({"A": {"count": 1, "last_error": "timeout"}, "B": {"count": 3, "last_error": "404"}})
    assert "## 取れなかった情報源" in s
    assert "- A: timeout" in s
    assert "- **B（3 日連続）**: 404" in s
    assert failures_section({}) == ""


def test_fallback_digest_lists_items_by_topic():
    d = fallback_digest("2026-09-14", [mk("a"), mk("b", topic="マーケ")], "claude -p が失敗")
    assert d.startswith("<!-- fallback -->\n# 2026-09-14 のダイジェスト")
    assert "要約は失敗しました（claude -p が失敗）" in d
    assert "### AI活用" in d and "### マーケ" in d
    assert "- [題 a](https://u/a)（S）" in d


import json
from datetime import datetime, timezone, timedelta

from summarize import summarize

JST = timezone(timedelta(hours=9))


def setup_inbox(tmp_path, items):
    inbox = tmp_path / "inbox"
    (inbox / "transcripts").mkdir(parents=True)
    (inbox / "items.json").write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "digest.md").write_text("# {DATE}\n{MATERIALS}", encoding="utf-8")
    (prompts / "item.md").write_text("{MATERIALS}", encoding="utf-8")
    return inbox, prompts


def test_summarize_writes_digest_and_archives_inbox(tmp_path):
    inbox, prompts = setup_inbox(tmp_path, [mk("a")])
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "failures.json").write_text('{"X": {"count": 1, "last_error": "e"}}', encoding="utf-8")
    calls = []
    def fake_run(prompt, **_):
        calls.append(prompt)
        return "# 2026-09-14 のダイジェスト\n\n## 今日のまとめ\nOK\n"
    now = datetime(2026, 9, 14, 5, 0, tzinfo=JST)
    out = summarize(inbox, tmp_path / "data", tmp_path / "state", tmp_path / "digest", prompts, run=fake_run, now=now, log=lambda *_: None)
    assert out == tmp_path / "digest" / "2026-09-14.md"
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# 2026-09-14 のダイジェスト")
    assert "## 取れなかった情報源\n- X: e" in text
    assert "=== 資料 1 ===" in calls[0] and "題 a" in calls[0]
    assert (tmp_path / "data" / "2026-09-14" / "items.json").exists()
    assert json.loads((inbox / "items.json").read_text(encoding="utf-8")) == []


def test_summarize_retries_once_then_falls_back(tmp_path):
    inbox, prompts = setup_inbox(tmp_path, [mk("a")])
    n = {"calls": 0}
    def bad_run(prompt, **_):
        n["calls"] += 1
        raise RuntimeError("枠切れ")
    now = datetime(2026, 9, 14, 5, 0, tzinfo=JST)
    out = summarize(inbox, tmp_path / "data", tmp_path / "state", tmp_path / "digest", prompts, run=bad_run, now=now, retry_wait=0, log=lambda *_: None)
    assert n["calls"] == 2
    text = out.read_text(encoding="utf-8")
    assert text.startswith("<!-- fallback -->") and "題 a" in text


def test_summarize_with_empty_inbox_writes_no_news(tmp_path):
    inbox, prompts = setup_inbox(tmp_path, [])
    def fake_run(prompt, **_):
        return "# 2026-09-14 のダイジェスト\n\n## 今日のまとめ\n新着なし\n"
    now = datetime(2026, 9, 14, 5, 0, tzinfo=JST)
    out = summarize(inbox, tmp_path / "data", tmp_path / "state", tmp_path / "digest", prompts, run=fake_run, now=now, log=lambda *_: None)
    assert "新着なし" in out.read_text(encoding="utf-8")
