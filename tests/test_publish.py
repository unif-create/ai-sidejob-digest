from publish import build_site, render_page


def test_render_page_has_noindex_viewport_and_footer():
    html = render_page("# 見出し\n\n本文 **強調**", "2026-09-14", [("2026-09-13", "archive/2026-09-13.html")])
    assert '<meta name="robots" content="noindex">' in html
    assert '<meta name="viewport"' in html
    assert "<h1>見出し</h1>" in html and "<strong>強調</strong>" in html
    assert 'href="archive/2026-09-13.html">2026-09-13' in html
    assert "ユニフ" in html
    assert "<title>2026-09-14 AI副業ニュース</title>" in html


def test_build_site_writes_index_and_archive(tmp_path):
    digest, site = tmp_path / "digest", tmp_path / "site"
    digest.mkdir()
    for d in ("2026-09-12", "2026-09-13", "2026-09-14"):
        (digest / f"{d}.md").write_text(f"# {d} のダイジェスト\n\n## 今日のまとめ\n中身 {d}\n", encoding="utf-8")
    written = build_site(digest, site, days=2)
    index = (site / "index.html").read_text(encoding="utf-8")
    assert "中身 2026-09-14" in index
    assert 'href="archive/2026-09-13.html"' in index and "2026-09-12.html" not in index
    assert (site / "archive" / "2026-09-14.html").exists()
    assert (site / "archive" / "2026-09-12.html").exists()
    assert 'href="../archive/2026-09-13.html"' in (site / "archive" / "2026-09-14.html").read_text(encoding="utf-8")
    assert set(p.name for p in written) == {"index.html", "2026-09-12.html", "2026-09-13.html", "2026-09-14.html"}


def test_build_site_without_digests(tmp_path):
    digest = tmp_path / "digest"
    digest.mkdir()
    build_site(digest, tmp_path / "site")
    assert "まだありません" in (tmp_path / "site" / "index.html").read_text(encoding="utf-8")


from publish import sanitize_html


def test_sanitize_html_strips_script_and_event_handlers():
    out = sanitize_html('<p>ok</p><script>alert(1)</script><img src=x onerror="alert(1)">')
    assert "<script>" not in out and "alert(1)" not in out
    assert "onerror" not in out
    assert "<p>ok</p>" in out


def test_sanitize_html_strips_javascript_href_but_keeps_normal_link():
    out = sanitize_html('<a href="javascript:alert(1)">bad</a><a href="https://x/">good</a>')
    assert "javascript:" not in out
    assert 'href="https://x/"' in out and ">good</a>" in out


def test_sanitize_html_drops_iframe_and_style_tags():
    out = sanitize_html('<iframe src="//evil"></iframe><style>body{}</style><b>b</b>')
    assert "<iframe" not in out and "<style" not in out and "<b>b</b>" in out
