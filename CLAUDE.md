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
- ダイジェストの本文は外部フィードのタイトル・概要を Claude が引用して作るので、HTML化するときは必ず `publish.sanitize_html` を通す（許可タグのホワイトリスト方式。2026-09-13 公開前レビューで追加）

## 運用

- タスクスケジューラ: `AI副業ニュース_夕方収集`（18:00、`collect`）と `AI副業ニュース_朝まとめ`（05:00、`all`）。履歴は `schtasks /Query /TN <名前> /V /FO LIST`
- ログ: `logs/run_YYYY-MM-DD.log`（Python）と `logs/bat_YYYY-MM-DD.log`（bat）
- ページが 2 日更新されていなければ、まず bat のログ → タスクスケジューラの履歴の順に見る
- 月 1 回 `pip install -U yt-dlp`
- 枠の消費が重いときは `prompts/digest.md` を「1 本 3 行だけ」に差し替える（コードは変えない）
- 公開 URL: https://unif-create.github.io/ai-sidejob-digest/
