import pytest
from sources import load_sources, Source


def write(tmp_path, text):
    p = tmp_path / "sources.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_youtube_and_rss_are_loaded(tmp_path):
    p = write(tmp_path, """
- name: "A"
  type: youtube
  id: "UC123"
  lang: ja
  topic: AI活用
- name: "B"
  type: rss
  id: "https://example.com/feed"
  lang: en
""")
    srcs = load_sources(p)
    assert srcs[0] == Source("A", "youtube", "UC123", "ja", "AI活用")
    assert srcs[0].feed_url == "https://www.youtube.com/feeds/videos.xml?channel_id=UC123"
    assert srcs[1].topic == "その他"
    assert srcs[1].feed_url == "https://example.com/feed"


def test_unknown_type_is_rejected(tmp_path):
    p = write(tmp_path, '- {name: A, type: twitter, id: x, lang: ja}')
    with pytest.raises(ValueError, match="type"):
        load_sources(p)


def test_duplicate_name_is_rejected(tmp_path):
    p = write(tmp_path, """
- {name: A, type: rss, id: "https://a", lang: ja}
- {name: A, type: rss, id: "https://b", lang: ja}
""")
    with pytest.raises(ValueError, match="重複"):
        load_sources(p)


def test_real_sources_yaml_is_valid():
    srcs = load_sources("sources.yaml")
    assert len([s for s in srcs if s.type == "youtube"]) == 10
    assert len([s for s in srcs if s.type == "rss"]) == 8
