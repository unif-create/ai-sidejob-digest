"""入口。python run.py collect|summarize|publish|all"""
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
LOGS = ROOT / "logs"


def _logger():
    LOGS.mkdir(exist_ok=True)
    path = LOGS / f"run_{datetime.now():%Y-%m-%d}.log"
    def log(*parts):
        line = f"[{datetime.now():%H:%M:%S}] " + " ".join(str(p) for p in parts)
        print(line)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    return log


def stage_collect(log):
    from collect import collect
    from sources import load_sources
    log("収集", collect(load_sources(ROOT / "sources.yaml"), log=log))


def stage_summarize(log):
    from summarize import summarize
    log("要約", summarize(log=log))


def stage_publish(log):
    from publish import build_site, git_publish
    build_site()
    log("公開 push:", git_publish(message=f"ダイジェストを更新 {datetime.now():%Y-%m-%d}"))


STAGES = {"collect": ["stage_collect"], "summarize": ["stage_summarize"], "publish": ["stage_publish"],
          "all": ["stage_collect", "stage_summarize", "stage_publish"]}


def main(argv) -> int:
    if len(argv) != 1 or argv[0] not in STAGES:
        print("使い方: python run.py collect|summarize|publish|all")
        return 2
    log = _logger()
    log("開始", argv[0])
    module = sys.modules[__name__]
    for stage_name in STAGES[argv[0]]:
        stage = getattr(module, stage_name)  # モジュール属性を呼び出し時に引く。テストで monkeypatch できるように
        try:
            stage(log)
        except Exception as e:
            log("失敗", stage_name, repr(e))
            return 1
    log("終了")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
