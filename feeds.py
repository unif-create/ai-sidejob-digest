"""フィードを取得して Item の辞書に変換する。ページ本体は取りに行かない。"""
import html
import re
import urllib.request
from datetime import datetime, timezone

import feedparser

from sources import Source

USER_AGENT = "Mozilla/5.0 (ai-sidejob-digest; personal feed reader)"
_TAG = re.compile(r"<[^>]+>")


def strip_html(s: str) -> str:
    return html.unescape(_TAG.sub("", s or "")).strip()


def _published(entry) -> str:
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if t:
        return datetime(*t[:6], tzinfo=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def _summary(entry) -> str:
    raw = entry.get("summary") or entry.get("media_description") or ""
    if not raw and entry.get("media_group"):
        raw = entry["media_group"][0].get("media_description", "") if isinstance(entry["media_group"], list) else ""
    return strip_html(raw)


def parse_feed(text: str, source: Source) -> list[dict]:
    parsed = feedparser.parse(text)
    items = []
    for e in parsed.entries:
        link = e.get("link", "")
        if source.type == "youtube":
            vid = e.get("yt_videoid") or re.sub(r".*v=", "", link)
            item_id = f"yt:{vid}"
            link = f"https://www.youtube.com/watch?v={vid}"
        else:
            item_id = e.get("id") or link
        items.append({
            "id": item_id,
            "source": source.name,
            "type": source.type,
            "title": strip_html(e.get("title", "")),
            "url": link,
            "published": _published(e),
            "lang": source.lang,
            "topic": source.topic,
            "summary": _summary(e),
        })
    return items


def fetch_feed(source: Source, timeout: int = 20) -> list[dict]:
    req = urllib.request.Request(source.feed_url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        text = r.read().decode("utf-8", errors="replace")
    return parse_feed(text, source)
