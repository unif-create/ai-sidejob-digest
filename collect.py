"""収集: sources.yaml の各フィードから新着を拾い、YouTube は字幕を取り、data/inbox に溜める。
情報源ごとに独立して処理し、1 つ失敗しても他は続ける。"""
from datetime import datetime, timezone
from pathlib import Path

from feeds import fetch_feed
from sources import load_sources
from state import load_json, record_result, save_json, split_new
from transcript import fetch_transcript

ROOT = Path(__file__).parent
INBOX = ROOT / "data" / "inbox"
STATE = ROOT / "state"


def _attach_transcript(item, inbox_dir: Path, get_transcript, log):
    item.update({"transcript_file": None, "transcript_lang": None, "duration_sec": None})
    if item["type"] != "youtube":
        return
    vid = item["id"].split(":", 1)[1]
    try:
        r = get_transcript(vid, inbox_dir / "yt_work")
    except Exception as e:  # 字幕が取れなくても Item は残す
        log(f"  字幕取得に失敗 {vid}: {e}")
        return
    if r is None:
        log(f"  字幕なし {vid}")
        return
    out = inbox_dir / "transcripts" / f"{vid}.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(r["text"], encoding="utf-8")
    item.update({"transcript_file": f"transcripts/{vid}.txt", "transcript_lang": r["lang"], "duration_sec": r["duration_sec"]})


def collect(sources, inbox_dir: Path = INBOX, state_dir: Path = STATE, *, fetch=fetch_feed,
            get_transcript=fetch_transcript, now: datetime | None = None, log=print) -> dict:
    now = now or datetime.now(timezone.utc)
    inbox_dir, state_dir = Path(inbox_dir), Path(state_dir)
    items = load_json(inbox_dir / "items.json", [])
    known = {it["id"] for it in items}
    seen = load_json(state_dir / "seen.json", {"ids": [], "sources": []})
    failures = load_json(state_dir / "failures.json", {})
    added, failed = 0, []
    for src in sources:
        try:
            fetched = fetch(src)
            new, seen = split_new(fetched, seen, src.name, now)
            log(f"{src.name}: {len(fetched)} 件中 新着 {len(new)}")
            for it in new:
                if it["id"] in known:
                    continue
                it["collected_at"] = now.isoformat()
                _attach_transcript(it, inbox_dir, get_transcript, log)
                items.append(it)
                known.add(it["id"])
                added += 1
            failures = record_result(failures, src.name, None, now)
        except Exception as e:
            log(f"{src.name}: 失敗 {e}")
            failures = record_result(failures, src.name, str(e), now)
            failed.append(src.name)
        save_json(inbox_dir / "items.json", items)
        save_json(state_dir / "seen.json", seen)
        save_json(state_dir / "failures.json", failures)
    return {"new": added, "failed": failed}


if __name__ == "__main__":
    print(collect(load_sources(ROOT / "sources.yaml")))
