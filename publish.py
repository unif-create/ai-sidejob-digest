"""公開: digest/*.md を HTML にしてリポジトリ直下に置き、git で push する。"""
import subprocess
from pathlib import Path

import markdown

ROOT = Path(__file__).parent
DIGEST = ROOT / "digest"

CSS = """
html{color-scheme:light}body{margin:0;background:#fff;color:#111;font-family:-apple-system,"Segoe UI","Hiragino Sans","Noto Sans JP",sans-serif;line-height:1.7;overflow-wrap:anywhere}
main{max-width:40rem;margin:0 auto;padding:1rem 1.2rem 3rem}h1{font-size:1.4rem;margin:.6rem 0 1rem;border-bottom:2px solid #111;padding-bottom:.3rem}
h2{font-size:1.15rem;margin:1.8rem 0 .5rem;border-left:4px solid #111;padding-left:.5rem}h3{font-size:1.02rem;margin:1.2rem 0 .3rem}h4{font-size:.98rem;margin:1rem 0 .2rem}
p,li{font-size:.95rem}a{color:#111;overflow-wrap:anywhere}nav{font-size:.85rem;margin-top:2.5rem;border-top:1px solid #999;padding-top:.8rem}nav a{margin-right:.6rem;white-space:nowrap}
footer{font-size:.8rem;color:#555;margin-top:2rem}
"""


def render_page(md_text: str, title: str, archive_links: list[tuple[str, str]]) -> str:
    body = markdown.markdown(md_text, extensions=["nl2br"])
    links = " ".join(f'<a href="{href}">{label}</a>' for label, href in archive_links)
    return (
        "<!doctype html><html lang=\"ja\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<meta name=\"robots\" content=\"noindex\">"
        f"<title>{title} AI副業ニュース</title><style>{CSS}</style></head><body><main>"
        f"{body}<nav>過去のダイジェスト: {links or 'なし'}</nav>"
        "<footer>AI副業ニュース — 集めた動画・記事を Claude Code で要約した個人用ダイジェスト。作者: ユニフ</footer>"
        "</main></body></html>"
    )


def _digests(digest_dir: Path) -> list[Path]:
    return sorted(Path(digest_dir).glob("????-??-??.md"))


def build_site(digest_dir: Path = DIGEST, site_root: Path = ROOT, days: int = 30) -> list[Path]:
    site_root = Path(site_root)
    archive_dir = site_root / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    files = _digests(digest_dir)
    written = []
    if not files:
        p = site_root / "index.html"
        p.write_text(render_page("# AI副業ニュース\n\nダイジェストはまだありません。", "AI副業ニュース", []), encoding="utf-8")
        return [p]
    recent = files[-days:]
    for f in files:
        others = [(o.stem, f"../archive/{o.stem}.html") for o in reversed(recent) if o != f]
        p = archive_dir / f"{f.stem}.html"
        p.write_text(render_page(f.read_text(encoding="utf-8"), f.stem, others), encoding="utf-8")
        written.append(p)
    latest = files[-1]
    others = [(o.stem, f"archive/{o.stem}.html") for o in reversed(recent) if o != latest]
    index = site_root / "index.html"
    index.write_text(render_page(latest.read_text(encoding="utf-8"), latest.stem, others), encoding="utf-8")
    written.append(index)
    return written


def git_publish(repo_dir: Path = ROOT, message: str = "ダイジェストを更新", runner=subprocess.run) -> bool:
    def git(*args):
        return runner(["git", *args], cwd=str(repo_dir), capture_output=True, encoding="utf-8", errors="replace")
    git("add", "index.html", "archive", "digest")
    if git("diff", "--cached", "--quiet").returncode == 0:
        return True  # 差分なし
    r = git("commit", "-m", message)
    if r.returncode != 0:
        return False
    r = git("push", "origin", "main")
    return r.returncode == 0


if __name__ == "__main__":
    build_site()
    print("push:", git_publish())
