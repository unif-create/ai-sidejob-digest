"""sources.yaml を読み、検証して Source の一覧にする。"""
from dataclasses import dataclass
from pathlib import Path

import yaml

VALID_TYPES = {"youtube", "rss"}
VALID_LANGS = {"ja", "en"}
DEFAULT_TOPIC = "その他"


@dataclass(frozen=True)
class Source:
    name: str
    type: str
    id: str
    lang: str
    topic: str = DEFAULT_TOPIC

    @property
    def feed_url(self) -> str:
        if self.type == "youtube":
            return f"https://www.youtube.com/feeds/videos.xml?channel_id={self.id}"
        return self.id


def load_sources(path: str | Path = "sources.yaml") -> list[Source]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []
    out: list[Source] = []
    names: set[str] = set()
    for i, r in enumerate(raw):
        for key in ("name", "type", "id", "lang"):
            if key not in r:
                raise ValueError(f"sources[{i}]: {key} がない")
        if r["type"] not in VALID_TYPES:
            raise ValueError(f"sources[{i}] {r['name']}: type は youtube か rss ({r['type']})")
        if r["lang"] not in VALID_LANGS:
            raise ValueError(f"sources[{i}] {r['name']}: lang は ja か en ({r['lang']})")
        if r["name"] in names:
            raise ValueError(f"sources[{i}]: name が重複 ({r['name']})")
        names.add(r["name"])
        out.append(Source(str(r["name"]), r["type"], str(r["id"]), r["lang"], str(r.get("topic") or DEFAULT_TOPIC)))
    return out
