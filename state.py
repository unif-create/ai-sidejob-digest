"""処理済み ID と失敗回数の記録。日付ではなく ID で判定する。"""
import json
from datetime import datetime, timedelta
from pathlib import Path


def load_json(path, default):
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(path, obj) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def split_new(items, seen, source_name, now: datetime, first_run_hours: int = 24):
    ids = set(seen.get("ids", []))
    sources = list(seen.get("sources", []))
    first_run = source_name not in sources
    cutoff = now - timedelta(hours=first_run_hours)
    new = []
    for it in items:
        if it["id"] in ids:
            continue
        ids.add(it["id"])
        if first_run and datetime.fromisoformat(it["published"]) < cutoff:
            continue
        new.append(it)
    if first_run:
        sources.append(source_name)
    return new, {"ids": sorted(ids), "sources": sources}


def record_result(failures, source_name, error, now: datetime):
    f = dict(failures)
    if error is None:
        f.pop(source_name, None)
        return f
    prev = f.get(source_name, {}).get("count", 0)
    f[source_name] = {"count": prev + 1, "last_error": str(error)[:200], "last_at": now.isoformat()}
    return f
