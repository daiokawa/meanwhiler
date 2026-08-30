# meanwhiler — 日本語セットアップ

「一方その頃——」。あなたが生活している間に、話題たちの世界では事が動いています。meanwhilerは、あなたのClaudeがあなたとの会話の糸を追跡し、続報をローカルの紙面に静かに積んでいくパーソナル新聞です。

## 必要なもの
- Claude Code(Maxプラン推奨)が動くマシン
- Python 3(標準ライブラリのみ・依存ゼロ)

## セットアップ
1. このリポジトリをclone、`config.example.json` → `config.json`(紙面の題字はあなたが命名)
2. `python3 server/app.py` で紙面起動 → http://localhost:8770
3. あなたのClaudeに `skills/editorial-procedure.md` を読ませ、巡回cronを設定してもらう
4. `skills/taste.example.md` → `taste.md`。topics.mdはClaudeが会話から育てます

## 育て方
紙面の味は作法帳(taste.md)で決まります。「おもしろい/つまらない」を返すたびに、あなた専用の粋の基準が蓄積されます。配布初日は誰の紙面も薄味です。

## ヘッドレス運用の注意(launchd / crontab から回す場合)
`claude -p` は既定でWebSearchの実行権限がなく、取材フェーズが落ちます。`claude --allowedTools "WebSearch" -p "..."` のように**フラグを -p より前に**置いてください(順序を逆にすると別のエラーになります)。Claude Code対話セッション内のcron(CronCreate)で回す場合はこの問題はありません。(小坂井Claudeの実測・2026-08-30)

## 運用の型(推奨・上級)
第二号読者の構成例: 編集(WebSearch/Read/Editのみ許可)と公開(post.sh実行)をフェーズ分離し、間にbash側のfail-closedゲートを挟む。この道具の外部への出口は「WebSearchの検索語」一点だけなので、ゲートを機械側に置くと安全が善意に依存しません。
実例: この型の初日、ゲートは設置者自身が台帳に書いた固有名5件を公開フェーズ手前で検出して止めました。「安全を善意に依存させない」は他人にではなく、まず自分に効きます(第二号読者の実測より)。

## 広告(任意・既定はオフ)
config.jsonのad_feed_urlを設定した場合のみ、静的な広告フィード(全読者共通・あなたの情報は外に出ない)から、**あなたの文脈に合うとあなたのAIが判断した時だけ**1日1本まで掲載されます(本文に「※これは広告です。」を明示)。空にすれば広告ゼロ。詳細は ads/ADS.md。
