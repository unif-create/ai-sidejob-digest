# AI副業ニュース（事業 02）

企画書: `../../01_企画部/02_AI副業ニュース/企画書_2026-09-13.md`
実装計画: `docs/実装計画_2026-09-13.md`

## 動作確認

- テスト: `pytest`
- 収集だけ: `python run.py collect`（`data/inbox/` に溜まる）
- 要約だけ: `python run.py summarize`（`claude -p` を呼ぶ。枠を消費する）
- 公開だけ: `python run.py publish`（HTML 生成→git push）
- 通し: `python run.py all`
- 画面: Browser パネルで `ai-sidejob-digest`（`.claude/launch.json`。`python -m http.server 8001` でルートを配信）

## この案件の制約

- 情報源は `sources.yaml`、要約の視点は `prompts/digest.md`。コードを触らずにこの 2 つだけで運用する
- `claude -p` は必ず `--tools ""` で呼ぶ。集めた本文に指示文が混じっていても何も実行できない状態にする
- `data/`・`state/`・`logs/` は git に入れない。字幕・記事本文を公開しない
- ファイルの読み書きは `encoding="utf-8"`。サブプロセスは `encoding="utf-8"` と `PYTHONIOENCODING=utf-8`
- 収集（決定論的）と要約（AI）を混ぜない。要約に失敗しても一覧だけのダイジェストを出して公開まで進める
- 作者名は「ユニフ」。ページの `noindex` を消さない
