#!/usr/bin/env python3
# what: ratings.jsonl を集計して ratings-digest.md を書き出す (meanwhiler)
# why : 編集局が執筆前に「何が刺さって何が刺さらなかったか」を一枚で読めるようにする
import json
import os
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
FEED = os.path.join(BASE, "feed.jsonl")
RATINGS = os.path.join(BASE, "ratings.jsonl")
OUT = os.path.join(BASE, "ratings-digest.md")


def read_jsonl(path):
    rows = []
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    return rows


def avg(xs):
    return sum(xs) / len(xs) if xs else None


def main():
    articles = {a["ts"]: a for a in read_jsonl(FEED) if "ts" in a}
    rated = {}
    for r in read_jsonl(RATINGS):  # 同じtsは後から書いた方が勝ち
        if r.get("ts") in articles:
            rated[r["ts"]] = r

    if not rated:
        with open(OUT, "w", encoding="utf-8") as f:
            f.write("# 紙面の評価ダイジェスト\n\n評価がまだありません。\n")
        print("no ratings yet")
        return

    rows = []
    for ts, r in rated.items():
        a = articles[ts]
        rows.append({
            "ts": ts, "score": r["score"], "memo": r.get("memo", ""),
            "kind": a.get("kind", "?"), "hook": a.get("hook", ""),
        })
    rows.sort(key=lambda x: x["score"])

    by_kind = defaultdict(list)
    by_week = defaultdict(list)
    for x in rows:
        by_kind[x["kind"]].append(x["score"])
        by_week[x["ts"][:10]].append(x["score"])  # 日別

    scores = [x["score"] for x in rows]
    L = ["# 紙面の評価ダイジェスト", ""]
    L.append(f"評価済み **{len(rows)}本** / 全体平均 **{avg(scores):.1f}点**"
             f"(未評価 {len(articles) - len(rows)}本)")
    L.append("")

    L.append("## 種類別の平均点")
    L.append("")
    L.append("| 種類 | 平均 | 本数 |")
    L.append("|---|---|---|")
    for k, v in sorted(by_kind.items(), key=lambda kv: -avg(kv[1])):
        L.append(f"| {k} | {avg(v):.1f} | {len(v)} |")
    L.append("")

    L.append("## 刺さった記事(上位5本) — この方向を増やす")
    L.append("")
    for x in list(reversed(rows))[:5]:
        L.append(f"- **{x['score']}点** [{x['kind']}] {x['hook']}")
    L.append("")

    L.append("## 刺さらなかった記事(下位5本) — この方向は繰り返さない")
    L.append("")
    for x in rows[:5]:
        memo = f" ← **{x['memo']}**" if x["memo"] else ""
        L.append(f"- **{x['score']}点** [{x['kind']}] {x['hook']}{memo}")
    L.append("")

    memos = [x for x in rows if x["memo"]]
    if memos:
        L.append("## 大川さんが書いたひとこと(全件)")
        L.append("")
        for x in memos:
            L.append(f"- ({x['score']}点) 「{x['memo']}」 ← {x['hook'][:40]}")
        L.append("")

    days = sorted(by_week.items())[-7:]
    if len(days) > 1:
        L.append("## 直近の日別平均")
        L.append("")
        for d, v in days:
            L.append(f"- {d}: {avg(v):.1f}点 ({len(v)}本)")
        L.append("")

    L.append("---")
    L.append("")
    L.append("**読み方**: 点数を取りにいくと紙面が壊れる。"
             "低評価の理由を潰すことだけに使い、高評価の記事の形を真似しないこと。")
    L.append("")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"wrote {OUT} ({len(rows)} ratings, avg {avg(scores):.1f})")


if __name__ == "__main__":
    main()
