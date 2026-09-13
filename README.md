# AI副業ニュース

YouTube・note・Zenn・Qiita・公式発表の新着を毎日集め、Claude Code で「AI 副業を立ち上げている人に何が使えるか」の視点でダイジェストにして、GitHub Pages で読めるようにする個人用ツール。

## 動かし方

```
pip install -r requirements.txt
python run.py all
```

- `sources.yaml` に情報源を足す・消す
- `prompts/digest.md` で要約の視点を変える
- 月 1 回 `pip install -U yt-dlp`

## 公開 URL

https://unif-create.github.io/ai-sidejob-digest/
