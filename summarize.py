"""要約: data/inbox の資料を claude -p に渡してダイジェストを作り、digest/ に書く。"""
import os
import shutil
import subprocess
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from state import load_json, save_json

ROOT = Path(__file__).parent
INBOX = ROOT / "data" / "inbox"
DATA = ROOT / "data"
STATE = ROOT / "state"
DIGEST = ROOT / "digest"
PROMPTS = ROOT / "prompts"
TOKEN_LIMIT = 80_000


def estimate_tokens(text: str, lang: str) -> int:
    return len(text) // (2 if lang == "ja" else 4)


def _kind(it: dict) -> str:
    if it["type"] != "youtube":
        return "記事"
    if it.get("transcript_file"):
        mins = f" {it['duration_sec'] // 60} 分" if it.get("duration_sec") else ""
        return f"動画{mins}（字幕 {it['transcript_lang']}）"
    return "動画（概要欄のみ）"


def _body(it: dict, inbox_dir: Path, max_chars: int) -> str:
    text = it.get("summary") or ""
    if it.get("transcript_file"):
        p = Path(inbox_dir) / it["transcript_file"]
        if p.exists():
            text = p.read_text(encoding="utf-8")
    if len(text) > max_chars:
        text = text[:max_chars] + "…（以下略）"
    return text


def build_materials(items: list[dict], inbox_dir: Path, max_chars: int = 60000) -> str:
    blocks = []
    for n, it in enumerate(items, 1):
        blocks.append(
            f"=== 資料 {n} ===\n"
            f"タイトル: {it['title']}\n出典: {it['source']}\n言語: {it['lang']}\ntopic: {it['topic']}\n"
            f"種別: {_kind(it)}\nURL: {it['url']}\n公開: {it['published'][:10]}\n"
            f"--- 本文 ---\n{_body(it, inbox_dir, max_chars)}\n"
        )
    return "\n".join(blocks)


def build_prompt(template: str, materials: str, date_str: str) -> str:
    return template.replace("{DATE}", date_str).replace("{MATERIALS}", materials)


def failures_section(failures: dict) -> str:
    if not failures:
        return ""
    lines = ["## 取れなかった情報源"]
    for name, f in sorted(failures.items()):
        if f["count"] >= 3:
            lines.append(f"- **{name}（{f['count']} 日連続）**: {f['last_error']}")
        else:
            lines.append(f"- {name}: {f['last_error']}")
    return "\n".join(lines) + "\n"


def fallback_digest(date_str: str, items: list[dict], reason: str) -> str:
    by_topic = defaultdict(list)
    for it in items:
        by_topic[it["topic"]].append(it)
    out = [f"<!-- fallback -->\n# {date_str} のダイジェスト", "", "## 今日のまとめ",
           f"要約は失敗しました（{reason}）。新着の一覧だけ載せます。翌日の実行で再挑戦します。", "", "## 新着一覧"]
    if not items:
        out.append("新着なし")
    for topic, its in sorted(by_topic.items()):
        out.append(f"### {topic}")
        out.extend(f"- [{it['title']}]({it['url']})（{it['source']}）" for it in its)
        out.append("")
    return "\n".join(out) + "\n"
