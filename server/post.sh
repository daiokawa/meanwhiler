#!/bin/bash
# meanwhiler 紙面への投稿ヘルパー
# usage: post.sh <kind: 続報|雑談|趨勢|号外|セール|庭> <hook> <body> [sources(改行区切り)]
# 書き込み先はこのスクリプトと同じディレクトリの feed.jsonl (app.py の読み先と一致)
PY=$(command -v python3 || command -v python)
FEED_DIR="$(cd "$(dirname "$0")" && pwd)" "$PY" - "$1" "$2" "$3" "$4" << 'PYEOF'
import json, sys, datetime, os
kind, hook, body, sources = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else ""
entry = {
    "ts": datetime.datetime.now().isoformat(timespec="seconds"),
    "kind": kind, "hook": hook, "body": body,
    "sources": [s.strip() for s in sources.splitlines() if s.strip()],
}
path = os.path.join(os.environ["FEED_DIR"], "feed.jsonl")
with open(path, "a", encoding="utf-8") as f:
    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
print("posted:", hook[:40])
PYEOF
