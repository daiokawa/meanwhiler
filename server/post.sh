#!/bin/bash
# meanwhiler 紙面への投稿ヘルパー
# usage: post.sh <kind: 続報|雑談|趨勢|号外|セール|庭> <hook> <body> [sources(改行区切り)] [--dup-ok]
# 書き込み先はこのスクリプトと同じディレクトリの feed.jsonl (app.py の読み先と一致)
# what: 既報と話題が被っていたら既定で拒否する
# why : 既報チェックを編集局の自律に任せると守られない(同じ出来事が数日おきに再掲される)
PY=$(command -v python3 || command -v python)
FEED_DIR="$(cd "$(dirname "$0")" && pwd)" "$PY" - "$1" "$2" "$3" "$4" "$5" << 'PYEOF'
import json, sys, datetime, os, re

kind, hook, body = sys.argv[1], sys.argv[2], sys.argv[3]
sources = sys.argv[4] if len(sys.argv) > 4 else ""
dup_ok = "--dup-ok" in sys.argv[1:]

path = os.path.join(os.environ["FEED_DIR"], "feed.jsonl")
WINDOW_DAYS = 30
TOKEN_MIN = 3      # 3文字以上の語だけを固有名詞候補として見る
OVERLAP = 0.5      # 短い方の語数に対する共有率がこれ以上なら「同じ話題」とみなす


def tokens(text):
    # 日本語は漢字・カタカナの連なり、その他の言語は空白区切りの語を拾う
    jp = re.findall(r"[一-龥ァ-ヴー]+", text)
    other = re.findall(r"[A-Za-z][A-Za-z0-9'-]+", text)
    return {t for t in jp + [w.lower() for w in other] if len(t) >= TOKEN_MIN}


def recent_entries():
    if not os.path.isfile(path):
        return []
    cut = (datetime.datetime.now() - datetime.timedelta(days=WINDOW_DAYS)).isoformat()
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
                if d.get("ts", "") >= cut:
                    out.append(d)
            except Exception:
                pass
    return out


new = tokens(hook)
hits = []
if new and not dup_ok:
    for d in recent_entries():
        old = tokens(d.get("hook", ""))
        if not old:
            continue
        shared = new & old
        if len(shared) >= 2 and len(shared) / min(len(new), len(old)) >= OVERLAP:
            hits.append((d, sorted(shared)))

if hits:
    sys.stderr.write("REJECTED: this topic overlaps with what you already published.\n")
    for d, shared in hits[-5:]:
        sys.stderr.write(f"  {d['ts'][:16]} [{d.get('kind')}] {d.get('hook','')[:60]}\n")
        sys.stderr.write(f"    shared: {' / '.join(shared)}\n")
    sys.stderr.write("\nRead those headlines first.\n")
    sys.stderr.write("If there is genuinely NEW development, rewrite the body to cover only "
                     "the delta and re-run with --dup-ok as the 5th argument.\n")
    sys.stderr.write("If it is the same event reworded, do not publish it.\n")
    sys.exit(2)

entry = {
    "ts": datetime.datetime.now().isoformat(timespec="seconds"),
    "kind": kind, "hook": hook, "body": body,
    "sources": [s.strip() for s in sources.splitlines() if s.strip()],
}
with open(path, "a", encoding="utf-8") as f:
    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
print("posted:", hook[:40])
PYEOF
