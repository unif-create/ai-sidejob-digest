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


def _claude_cmd() -> list[str]:
    exe = shutil.which("claude")
    if not exe:
        raise RuntimeError("claude コマンドが見つからない")
    return [exe]


def run_claude(prompt: str, model: str = "sonnet", timeout: int = 900) -> str:
    """claude -p をツールなしで呼ぶ。資料に指示文が混じっていても何も実行できない。"""
    cmd = _claude_cmd() + ["-p", "--model", model, "--tools", "", "--output-format", "text", "--no-session-persistence"]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    env.pop("ANTHROPIC_API_KEY", None)
    r = subprocess.run(cmd, input=prompt, capture_output=True, encoding="utf-8", errors="replace", env=env, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"claude -p が終了コード {r.returncode}: {r.stderr[-500:]}")
    out = r.stdout.strip()
    if not out.startswith("#"):
        raise RuntimeError(f"出力がテンプレートの形でない: {out[:100]!r}")
    return out


def _archive_inbox(inbox_dir: Path, data_dir: Path, date_str: str) -> Path:
    dest = Path(data_dir) / date_str
    n = 2
    while dest.exists():
        dest = Path(data_dir) / f"{date_str}_{n}"
        n += 1
    shutil.move(str(inbox_dir), str(dest))
    (Path(inbox_dir) / "transcripts").mkdir(parents=True)
    save_json(Path(inbox_dir) / "items.json", [])
    return dest


def _run_with_retry(run, prompt, retry_wait, log):
    try:
        return run(prompt)
    except Exception as e:
        log(f"要約に失敗、{retry_wait} 秒後に再試行: {e}")
        time.sleep(retry_wait)
        return run(prompt)


def summarize_items_first(items: list[dict], inbox_dir: Path, item_template: str, run, log) -> list[dict]:
    """2 段目: 1 本ずつ 5 行に縮めてから束ねる。"""
    out = []
    for it in items:
        materials = build_materials([it], inbox_dir)
        try:
            short = run(build_prompt(item_template, materials, ""))
        except Exception as e:
            log(f"  1 本要約に失敗 {it['title'][:30]}: {e}")
            short = (it.get("summary") or "")[:500]
        out.append({**it, "summary": short, "transcript_file": None})
    return out


def _make_digest(items, inbox_dir, prompts_dir, date_str, run, retry_wait, log) -> str:
    template = (Path(prompts_dir) / "digest.md").read_text(encoding="utf-8")
    materials = build_materials(items, inbox_dir)
    est = estimate_tokens(materials, "ja")
    log(f"資料 {len(items)} 件、約 {est:,} トークン")
    if est > TOKEN_LIMIT:
        log("上限を超えるので 1 本ずつ要約してから束ねる")
        item_template = (Path(prompts_dir) / "item.md").read_text(encoding="utf-8")
        items = summarize_items_first(items, inbox_dir, item_template, run, log)
        materials = build_materials(items, inbox_dir)
    try:
        return _run_with_retry(run, build_prompt(template, materials, date_str), retry_wait, log)
    except Exception as e:
        log(f"要約を諦めて一覧だけ出す: {e}")
        return fallback_digest(date_str, items, str(e)[:80])


def retry_fallbacks(data_dir, digest_dir, prompts_dir, state_dir, *, run=run_claude, now=None,
                    days: int = 3, retry_wait: int = 0, log=print) -> list[Path]:
    now = (now or datetime.now(timezone.utc)).astimezone()
    done = []
    for p in sorted(Path(digest_dir).glob("*.md")):
        if not p.read_text(encoding="utf-8").startswith("<!-- fallback -->"):
            continue
        try:
            age = (now.date() - datetime.strptime(p.stem, "%Y-%m-%d").date()).days
        except ValueError:
            continue
        src = Path(data_dir) / p.stem
        if age > days or not (src / "items.json").exists():
            continue
        log(f"{p.name} の要約を作り直す")
        items = load_json(src / "items.json", [])
        body = _make_digest(items, src, prompts_dir, p.stem, run, retry_wait, log)
        if body.startswith("<!-- fallback -->"):
            continue
        p.write_text(body.rstrip() + "\n", encoding="utf-8")
        done.append(p)
    return done


def summarize(inbox_dir: Path = INBOX, data_dir: Path = DATA, state_dir: Path = STATE, digest_dir: Path = DIGEST,
              prompts_dir: Path = PROMPTS, *, run=run_claude, now: datetime | None = None,
              retry_wait: int = 600, log=print) -> Path:
    now = (now or datetime.now(timezone.utc)).astimezone()
    date_str = now.strftime("%Y-%m-%d")
    inbox_dir, digest_dir = Path(inbox_dir), Path(digest_dir)
    retry_fallbacks(data_dir, digest_dir, prompts_dir, state_dir, run=run, now=now, log=log)
    items = load_json(inbox_dir / "items.json", [])
    failures = load_json(Path(state_dir) / "failures.json", {})
    body = _make_digest(items, inbox_dir, prompts_dir, date_str, run, retry_wait, log)
    text = body.rstrip() + "\n\n" + failures_section(failures)
    digest_dir.mkdir(parents=True, exist_ok=True)
    out = digest_dir / f"{date_str}.md"
    out.write_text(text.rstrip() + "\n", encoding="utf-8")
    dest = _archive_inbox(inbox_dir, data_dir, date_str)
    log(f"ダイジェスト {out.name} を書き、資料を {dest.name} に移した")
    return out


if __name__ == "__main__":
    print(summarize())
