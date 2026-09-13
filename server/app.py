#!/usr/bin/env python3
# Claude says 新聞 - 雑談/号外/セールの専用紙面
# what: feed.jsonl を新聞風ページで配信する最小サーバー(標準ライブラリのみ)
# why : チャット履歴は流れて探しにくい。新着が一目で分かる置き場を分離する
import datetime
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = os.path.dirname(os.path.abspath(__file__))
FEED = os.path.join(BASE, "feed.jsonl")
RATINGS = os.path.join(BASE, "ratings.jsonl")
MEMO_MAX = 200
CONF = {}
for p in (os.path.join(BASE, "..", "config.json"), os.path.join(BASE, "config.json")):
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as f:
            CONF = json.load(f)
        break
PORT = int(CONF.get("port", 8770))
HOST = CONF.get("host", "127.0.0.1")
TITLE = CONF.get("paper_title", "続報と雑談")
TAGLINE = CONF.get("tagline", "あなた専用・不定期刊")
SRC_LABEL = CONF.get("source_label", "出典")
FOOTER = CONF.get("footer", "掲載基準: 未知・いま動いた・刺さる ／ 迷ったら黙る")
KINDS_MAP = CONF.get("kinds", {"雑談":"zatsudan","続報":"zokuho","号外":"gogai","セール":"sale","庭":"niwa","趨勢":"trend"})
# 1〜10の評価UIの文言(config.jsonのratingで差し替え可)
RATE = CONF.get("rating", {})
R_LO = RATE.get("low_label", "つまんない")
R_HI = RATE.get("high_label", "おもしろい")
R_PH = RATE.get("memo_placeholder", "どこがつまらなかったか(任意)")
R_SEND = RATE.get("send_label", "送信")
R_DONE = RATE.get("rated_label", "評価")


def load_ratings():
    # what: ratings.jsonl を ts -> {score, memo} に畳む(同じtsは後から書いた方が勝ち)
    out = {}
    if os.path.isfile(RATINGS):
        with open(RATINGS, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    out[r["ts"]] = {"score": r.get("score"), "memo": r.get("memo", "")}
                except Exception:
                    pass
    return out


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
    items = items[:120]  # 紙面は最新120本まで(過去分もfeed.jsonlには全部残る)
    rated = load_ratings()
    for it in items:
        r = rated.get(it.get("ts"))
        if r:
            it["score"] = r["score"]
            it["memo"] = r["memo"]
    return items


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
  .rate { margin-top:14px; display:flex; align-items:center; gap:6px; flex-wrap:wrap; }
  .rate .cap { font-size:11px; color:#b5b0a6; letter-spacing:1px; }
  .rate .btns { display:flex; gap:3px; }
  .rate button { width:27px; height:27px; padding:0; cursor:pointer; font-size:12px;
                 border:1px solid var(--line); background:#fff; color:#8a857b; border-radius:3px;
                 font-family:inherit; }
  .rate button:hover { border-color:#a8a29a; color:var(--ink); }
  .rate button.on { color:#fff; font-weight:700; border-color:transparent; }
  .rate button.on.lo { background:var(--red); }
  .rate button.on.mid { background:#8a857b; }
  .rate button.on.hi { background:var(--blue); }
  .rate button.on.top { background:var(--green); }
  .memo { margin-top:8px; display:flex; gap:6px; }
  .memo input { flex:1; font-family:inherit; font-size:13px; padding:6px 9px;
                border:1px solid var(--line); border-radius:3px; background:#fff; color:var(--ink); }
  .memo button { width:auto; padding:0 12px; height:auto; }
  .done { font-size:11px; color:#8a857b; cursor:pointer; }
  .done .m { color:#b5b0a6; }
</style></head>
<body>
<header><h1>__TITLE__</h1><div class="tagline">__TAGLINE__</div></header>
<div class="wrap" id="feed"></div>
<footer>__FOOTER__</footer>
<script>
const KINDS = __KINDS__;

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
        const a = el("a","", "__SRC__"+(i+1));
        try{ const u = new URL(sv); if(u.protocol==="https:"||u.protocol==="http:") a.href = u.href; }catch(e){}
        a.target="_blank"; a.rel="noopener";
        sd.appendChild(a);
      });
      art.appendChild(sd);
    }
  }
  art.appendChild(buildRating(it));
  return art;
}

function band(n){ return n<=3 ? "lo" : n<=5 ? "mid" : n<=7 ? "hi" : "top"; }

// what: 1〜10の評価UI。5点以下だけ「ひとこと」欄が開く
// why : 点数だけでは"なぜ刺さらなかったか"が残らない。理由が要るのは失敗のときだけ
function buildRating(it){
  const holder = el("div");

  function showDone(score, memo){
    const d = el("div","done","__DONE__ " + score + "/10");
    if(memo) d.appendChild(el("span","m","  " + memo));
    d.onclick = ()=> showPicker(score);
    holder.replaceChildren(d);
  }

  function showPicker(current){
    holder.replaceChildren();
    const box = el("div","rate");
    box.appendChild(el("span","cap","__LO__"));
    const btns = el("div","btns");
    const memoWrap = el("div","memo");
    memoWrap.style.display = "none";
    const input = document.createElement("input");
    input.type = "text";
    input.maxLength = 200;
    input.placeholder = "__MEMOPH__";
    const send = el("button","","__SEND__");
    memoWrap.appendChild(input);
    memoWrap.appendChild(send);
    let picked = current || 0;

    function paint(){
      [...btns.children].forEach((b,i)=>{
        b.className = (i+1)===picked ? "on " + band(picked) : "";
      });
    }

    async function submit(score, memo){
      try{
        await fetch("/rate", {method:"POST", headers:{"Content-Type":"application/json"},
          body: JSON.stringify({ts: it.ts, score: score, memo: memo || ""})});
        it.score = score; it.memo = memo || "";
        showDone(score, memo || "");
      }catch(e){ send.textContent = "!"; }
    }

    for(let n=1; n<=10; n++){
      const b = el("button","", String(n));
      b.onclick = ()=>{
        picked = n; paint();
        if(n<=5){ memoWrap.style.display = "flex"; input.focus(); }
        else { submit(n, ""); }
      };
      btns.appendChild(b);
    }
    send.onclick = ()=> submit(picked, input.value.trim());

    // IME: 変換確定のEnterで送信しない。compositionendがkeydownより先に来る環境が
    // あるため、isComposing/keyCode229に加えて確定直後の猶予も見る
    let imeEnd = 0;
    input.addEventListener("compositionend", ()=>{ imeEnd = Date.now(); });
    input.addEventListener("keydown", (e)=>{
      if(e.key !== "Enter") return;
      if(e.isComposing || e.keyCode === 229) return;
      if(Date.now() - imeEnd < 300) return;
      e.preventDefault(); send.click();
    });

    box.appendChild(btns);
    box.appendChild(el("span","cap","__HI__"));
    paint();
    holder.appendChild(box);
    holder.appendChild(memoWrap);
  }

  if(it.score) showDone(it.score, it.memo || ""); else showPicker(0);
  return holder;
}

async function render(){
  // 入力中の再描画はメモを消してしまうので見送る
  if(document.activeElement && document.activeElement.tagName === "INPUT") return;
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
            page = (PAGE.replace("__TITLE__", TITLE).replace("__TAGLINE__", TAGLINE)
                    .replace("__KINDS__", json.dumps(KINDS_MAP, ensure_ascii=False))
                    .replace("__SRC__", SRC_LABEL).replace("__FOOTER__", FOOTER)
                    .replace("__LO__", R_LO).replace("__HI__", R_HI)
                    .replace("__MEMOPH__", R_PH).replace("__SEND__", R_SEND)
                    .replace("__DONE__", R_DONE))
            return self._send(200, page, "text/html; charset=utf-8")
        if self.path == "/feed.json":
            return self._send(200, json.dumps(load_feed(), ensure_ascii=False))
        return self._send(404, "{}")

    def do_POST(self):
        if self.path != "/rate":
            return self._send(404, "{}")
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0 or n > 4096:
                raise ValueError("bad length")
            req = json.loads(self.rfile.read(n))
            ts = str(req["ts"])[:32]
            score = int(req["score"])
            if not 1 <= score <= 10:
                raise ValueError("score out of range")
            memo = str(req.get("memo") or "").replace("\n", " ")[:MEMO_MAX]
        except Exception:
            return self._send(400, json.dumps({"ok": False}))
        entry = {
            "ts": ts,
            "score": score,
            "memo": memo,
            "rated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        with open(RATINGS, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return self._send(200, json.dumps({"ok": True}))


if __name__ == "__main__":
    print(f"meanwhiler: http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
