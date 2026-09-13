"""yt-dlp で字幕だけを取り、VTT を素のテキストにする。自宅 PC（住宅用 IP）で動かす前提。

この PC は Norton が全通信を TLS 中継しており、yt-dlp は SSL_CERT_FILE / REQUESTS_CA_BUNDLE を
見ないため証明書検証で失敗する（requests ライブラリでは通る。2026-09-13 確認）。yt-dlp にはカスタム
CA を指定する CLI オプションがなく、システムの証明書ストアを書き換えるのは避けたいので、この
youtube.com 向け呼び出しに限って --no-check-certificates を付ける。
"""
import html
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

_TIMING = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d{3} --> ")
_INLINE = re.compile(r"<[^>]+>")
_HEADER_KEYS = ("WEBVTT", "Kind:", "Language:")


def vtt_to_text(vtt: str) -> str:
    lines = []
    for raw in vtt.splitlines():
        line = raw.strip()
        if not line or _TIMING.match(line) or line.startswith(_HEADER_KEYS) or line.isdigit():
            continue
        line = html.unescape(_INLINE.sub("", line)).replace("\xa0", " ").strip()
        if not line:
            continue
        if lines and (line == lines[-1] or lines[-1].endswith(line) or line.startswith(lines[-1])):
            lines[-1] = line if len(line) >= len(lines[-1]) else lines[-1]
            continue
        lines.append(line)
    return "\n".join(lines)


def _ytdlp_cmd() -> list[str]:
    exe = shutil.which("yt-dlp")
    return [exe] if exe else ["python", "-m", "yt_dlp"]


def fetch_transcript(video_id: str, work_dir: Path, langs: tuple[str, ...] = ("ja", "en")) -> dict | None:
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    cmd = _ytdlp_cmd() + [
        "--skip-download", "--write-subs", "--write-auto-subs", "--no-check-certificates",
        "--sub-langs", ",".join(langs), "--sub-format", "vtt",
        "--write-info-json", "--sleep-requests", "1", "--no-warnings", "--quiet",
        "-o", str(work_dir / "%(id)s.%(ext)s"),
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", env=env, timeout=300)
    duration = None
    info = work_dir / f"{video_id}.info.json"
    if info.exists():
        d = json.loads(info.read_text(encoding="utf-8")).get("duration")
        duration = int(d) if d else None
    for lang in langs:
        for candidate in sorted(work_dir.glob(f"{video_id}.{lang}*.vtt")):
            text = vtt_to_text(candidate.read_text(encoding="utf-8"))
            if text:
                return {"text": text, "lang": lang, "duration_sec": duration}
    # 言語ごとに個別にダウンロードするので、片方の言語だけ 429 等で失敗しても
    # もう片方が取れていれば上の for ループで拾える。両方とも取れなかった場合のみエラーにする。
    if r.returncode != 0:
        raise RuntimeError(f"yt-dlp が終了コード {r.returncode}: {r.stderr[-300:]}")
    return None
