#!/usr/bin/env python3
# what: 出典ページの og:image を1枚だけ取ってきて images/ に保存する (meanwhiler)
# why : 紙面に写真を載せたい。直リンクだと開くたびに読者のアクセスが相手先に残り、
#       相手が消せば紙面からも消える。掲載時に一度だけ取って手元に置く
import ipaddress
import json
import os
import socket
import urllib.error
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

BASE = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE, "images")
TIMEOUT = 8
MAX_PAGE = 1_000_000
MAX_IMG = 5_000_000
UA = "Mozilla/5.0 (compatible; meanwhiler thumbnail)"


def enabled():
    for p in (os.path.join(BASE, "..", "config.json"), os.path.join(BASE, "config.json")):
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f).get("images", True)
    return True


def _public(url):
    # 手元の機械やLAN内を取りに行かない(出典URLは編集局が書くので信用しない)
    u = urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        return False
    try:
        infos = socket.getaddrinfo(u.hostname, None)
    except OSError:
        return False
    return bool(infos) and all(ipaddress.ip_address(i[4][0].split("%")[0]).is_global for i in infos)


class _CheckedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _public(newurl):
            raise urllib.error.URLError("redirect to non-public address")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_opener = urllib.request.build_opener(_CheckedRedirect)


def _get(url, limit):
    if not _public(url):
        return None, None
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with _opener.open(req, timeout=TIMEOUT) as r:
        data = r.read(limit + 1)
        final = r.geturl()
    return (None, None) if len(data) > limit else (data, final)


class _Meta(HTMLParser):
    def __init__(self):
        super().__init__()
        self.found = {}

    def handle_starttag(self, tag, attrs):
        if tag != "meta":
            return
        a = dict(attrs)
        key = (a.get("property") or a.get("name") or "").lower()
        if key in ("og:image", "og:image:secure_url", "twitter:image") and a.get("content"):
            self.found.setdefault(key, a["content"])


def _ext(data):
    # 中身で判定する(拡張子やContent-Typeは信用しない)。SVGはスクリプトを含みうるので扱わない
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:4] == b"GIF8":
        return ".gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return None


def fetch(sources, ts):
    """最初に画像が取れた出典の og:image を保存し、ファイル名を返す。取れなければ None"""
    if not enabled():
        return None
    for src in sources[:3]:
        try:
            page, final = _get(src, MAX_PAGE)
            if not page:
                continue
            p = _Meta()
            p.feed(page.decode("utf-8", "replace"))
            img_url = next((p.found[k] for k in ("og:image", "og:image:secure_url", "twitter:image")
                            if k in p.found), None)
            if not img_url:
                continue
            data, _ = _get(urljoin(final, img_url.strip()), MAX_IMG)
            ext = _ext(data or b"")
            if not ext:
                continue
            os.makedirs(IMG_DIR, exist_ok=True)
            name = ts.replace(":", "-") + ext
            with open(os.path.join(IMG_DIR, name), "wb") as f:
                f.write(data)
            return name
        except Exception:
            continue
    return None


if __name__ == "__main__":
    import sys
    print(fetch(sys.argv[2:], sys.argv[1]))
