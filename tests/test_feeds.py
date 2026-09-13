from pathlib import Path

from feeds import parse_feed, strip_html
from sources import Source

FIX = Path(__file__).parent / "fixtures"
YT = Source("テストチャンネル", "youtube", "UC123", "ja", "AI活用")
NOTE = Source("note: ぶべ", "rss", "https://note.com/bubecode/rss", "ja", "個人開発")


def test_strip_html():
    assert strip_html("<p>a</p> <b>b</b>&amp;") == "a b&"


def test_youtube_entries_become_items():
    items = parse_feed((FIX / "youtube.xml").read_text(encoding="utf-8"), YT)
    assert len(items) == 2
    it = items[0]
    assert it["id"] == "yt:abc123"
    assert it["source"] == "テストチャンネル"
    assert it["type"] == "youtube"
    assert it["title"] == "テスト動画 1"
    assert it["url"] == "https://www.youtube.com/watch?v=abc123"
    assert it["published"] == "2026-09-13T08:00:00+00:00"
    assert it["lang"] == "ja" and it["topic"] == "AI活用"
    assert it["summary"] == "概要欄のテキスト 太字"


def test_rss_entries_become_items():
    items = parse_feed((FIX / "note.xml").read_text(encoding="utf-8"), NOTE)
    it = items[0]
    assert it["id"] == "https://note.com/bubecode/n/n1"
    assert it["type"] == "rss"
    assert it["published"] == "2026-09-13T08:00:00+00:00"  # +0900 を UTC に直す
    assert it["summary"] == "記事の冒頭です。"


def test_entry_without_date_gets_now():
    xml = '<rss version="2.0"><channel><item><title>t</title><link>https://x/1</link></item></channel></rss>'
    it = parse_feed(xml, NOTE)[0]
    assert it["id"] == "https://x/1"
    assert it["published"].endswith("+00:00")
