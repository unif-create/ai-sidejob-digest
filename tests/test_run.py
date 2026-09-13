import run
from publish import git_publish


class FakeRunner:
    def __init__(self, fail_push=False):
        self.calls, self.fail_push = [], fail_push

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        class R: returncode = 0; stdout = ""; stderr = ""
        r = R()
        if cmd[:2] == ["git", "diff"]:
            r.returncode = 1          # 差分あり
        if cmd[:2] == ["git", "push"] and self.fail_push:
            r.returncode = 1; r.stderr = "network"
        return r


def test_git_publish_commits_and_pushes(tmp_path):
    runner = FakeRunner()
    assert git_publish(tmp_path, "更新", runner=runner) is True
    verbs = [c[1] for c in runner.calls]
    assert verbs == ["add", "diff", "commit", "push"]


def test_git_publish_returns_false_when_push_fails(tmp_path):
    assert git_publish(tmp_path, "更新", runner=FakeRunner(fail_push=True)) is False


def test_main_runs_stages_in_order(monkeypatch, tmp_path):
    order = []
    monkeypatch.setattr(run, "stage_collect", lambda log: order.append("collect"))
    monkeypatch.setattr(run, "stage_summarize", lambda log: order.append("summarize"))
    monkeypatch.setattr(run, "stage_publish", lambda log: order.append("publish"))
    monkeypatch.setattr(run, "LOGS", tmp_path)
    assert run.main(["all"]) == 0
    assert order == ["collect", "summarize", "publish"]
    assert run.main(["collect"]) == 0
    assert order[-1] == "collect"
    assert list(tmp_path.glob("run_*.log"))
