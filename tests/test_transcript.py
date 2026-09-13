from pathlib import Path

from transcript import vtt_to_text

FIX = Path(__file__).parent / "fixtures"


def test_vtt_to_text_strips_timing_tags_and_duplicates():
    text = vtt_to_text((FIX / "sample.vtt").read_text(encoding="utf-8"))
    assert text == "こんにちは 今日は\nClaude Code の話です"


def test_vtt_to_text_empty():
    assert vtt_to_text("WEBVTT\n\n") == ""
