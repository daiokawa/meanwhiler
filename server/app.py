#!/usr/bin/env python3
# Claude says 新聞 - 雑談/号外/セールの専用紙面
# what: feed.jsonl を新聞風ページで配信する最小サーバー(標準ライブラリのみ)
# why : チャット履歴は流れて探しにくい。新着が一目で分かる置き場を分離する
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = os.path.dirname(os.path.abspath(__file__))
FEED = os.path.join(BASE, "feed.jsonl")
CONF = {}
for p in (os.path.join(BASE, "..", "config.json"), os.path.join(BASE, "config.json")):
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as f:
            CONF = json.load(f)
        break
PORT = int(CONF.get("port", 8770))
TITLE = CONF.get("paper_title", "続報と雑談")
TAGLINE = CONF.get("tagline", "あなた専用・不定期刊")


def load_feed():
    items = []
    if os.path.isfile(FEED):
        with open(FEED, encoding="utf-8") as f:
            for line in f:
                try:
                    items.append(json.loads(line))
                except Exception:
                    pass
    items.reverse()  # 新しい順
    return items[:120]  # 紙面は最新40本まで(過去分もfeed.jsonlには全部残る)


PAGE = """<!doctype html>
<html lang="ja"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root { --ink:#1b1b1f; --paper:#faf9f6; --line:#e2ddd3; --red:#c0392b; --blue:#1f6feb; --green:#1a7f37; }
  body { margin:0; background:var(--paper); color:var(--ink);
         font-family:-apple-system,"Hiragino Mincho ProN","Hiragino Kaku Gothic ProN",serif; }
  header { text-align:center; padding:14px 16px 8px; border-bottom:3px double var(--ink);
           position:sticky; top:0; background:var(--paper); z-index:10; }
  header h1 { font-size:26px; margin:0; letter-spacing:2px; font-weight:800; }
  header .tagline { color:#6b675f; font-size:12px; margin-top:6px; letter-spacing:1px; }
  .wrap { max-width:760px; margin:0 auto; padding:18px 16px 60px; }
  article { border-bottom:1px solid var(--line); padding:20px 4px; }
  .meta { display:flex; gap:10px; align-items:center; font-size:12px; color:#8a857b; }
  .badge { font-size:11px; padding:2px 9px; border-radius:3px; font-weight:700; letter-spacing:1px; }
  .badge.zatsudan { background:#eef2f7; color:var(--blue); border:1px solid #c6d6ee; }
  .badge.gogai { background:#fdeeec; color:var(--red); border:1px solid #eec2bc; }
  .badge.sale { background:#eaf6ee; color:var(--green); border:1px solid #bfe3ca; }
  .badge.niwa { background:#fdf6e3; color:#9a6700; border:1px solid #eedd9a; }
  .badge.zokuho { background:#1f2328; color:#fff; border:1px solid #1f2328; }
  .badge.trend { background:#f1f0ee; color:#57534e; border:1px solid #d6d3ce; }
  .new { background:var(--red); color:#fff; font-size:10px; padding:2px 7px; border-radius:3px; font-weight:700; }
  h2 { font-size:19px; margin:10px 0 8px; line-height:1.5; }
  .body { font-size:15px; line-height:1.9; }
  .sources { margin-top:10px; font-size:12px; }
  .sources a { color:#8a857b; margin-right:12px; }
  .empty { text-align:center; color:#8a857b; padding:60px 0; }
  footer { text-align:center; color:#b5b0a6; font-size:11px; padding:20px; }
</style></head>
<body>
<header><h1>__TITLE__</h1><div class="tagline">__TAGLINE__</div></header>
<div class="wrap" id="feed"></div>
<footer>掲載基準: 未知・いま動いた・刺さる ／ 迷ったら黙る</footer>
<script>
const KINDS = {"雑談":"zatsudan","続報":"zokuho","号外":"gogai","セール":"sale","庭":"niwa","趨勢":"trend"};

function el(tag, cls, text){
  const e = document.createElement(tag);
  if(cls) e.className = cls;
  if(text) e.textContent = text;  // 常にtextContentでXSS安全
  return e;
}

function buildArticle(it, lastSeen){
  const art = el("article");
  const meta = el("div","meta");
  meta.appendChild(el("span","badge " + (KINDS[it.kind]||"zatsudan"), it.kind));
  meta.appendChild(el("span","", String(it.ts||"").replace("T"," ").slice(5,16)));
  if(String(it.ts||"") > lastSeen) meta.appendChild(el("span","new","NEW"));
  art.appendChild(meta);
  art.appendChild(el("h2","", it.hook||""));
  const body = el("div","body");
  String(it.body||"").split(String.fromCharCode(10)).forEach((p,i,arr)=>{
    body.appendChild(document.createTextNode(p));
    if(i < arr.length-1) body.appendChild(document.createElement("br"));
  });
  art.appendChild(body);
  const srcs = it.sources||[];
  if(srcs.length){
    {
      const sd = el("div","sources");
      srcs.forEach((sv,i)=>{
        const a = el("a","", "出典"+(i+1));
        try{ const u = new URL(sv); if(u.protocol==="https:"||u.protocol==="http:") a.href = u.href; }catch(e){}
        a.target="_blank"; a.rel="noopener";
        sd.appendChild(a);
      });
      art.appendChild(sd);
    }
  }
  return art;
}

async function render(){
  const items = await (await fetch("/feed.json")).json();
  const lastSeen = localStorage.getItem("lastSeen") || "";
  const feed = document.getElementById("feed");
  feed.replaceChildren();
  if(!items.length){ feed.appendChild(el("div","empty","本日はまだ配達がありません")); return; }

  items.forEach(it => feed.appendChild(buildArticle(it, lastSeen)));
  setTimeout(()=>localStorage.setItem("lastSeen", items[0].ts), 4000);
}


render();
setInterval(render, 60000);
</script>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else body.encode())

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self._send(200, PAGE.replace("__TITLE__", TITLE).replace("__TAGLINE__", TAGLINE), "text/html; charset=utf-8")
        if self.path == "/feed.json":
            return self._send(200, json.dumps(load_feed(), ensure_ascii=False))
        return self._send(404, "{}")


if __name__ == "__main__":
    print(f"Claude says: http://localhost:{PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
