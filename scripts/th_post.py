"""Threads に投稿する（1本・ツリー・画像・カルーセル）。

公式の流れ：① 入れ物を作る（POST /{user}/threads）→ ② 平均30秒待つ → ③ 公開（POST /{user}/threads_publish）
ツリー（続き）は、1本目を公開したあと reply_to_id に1本目のIDを入れて2本目を作る…を繰り返します。

  python3 scripts/th_post.py --file drafts/2026-11-01-0800.md          # 何が送られるか見るだけ
  python3 scripts/th_post.py --file drafts/2026-11-01-0800.md --go     # 本当に投稿
  python3 scripts/th_post.py --text "ひとこと" --go

drafts の md の書き方（templates/post.md）：
  ## 1投稿目   ← ここだけなら1本
  ## 2投稿目   ← あればツリーとして続ける（最大10本まで・このキットの決まり）
  - topic: 家計簿        （任意・トピックは1つだけ・50字まで・「.」「&」は使えない）
  - image: https://...   （任意・1投稿目に画像。2つ以上でカルーセル）
"""
from __future__ import annotations

import os as _ng_os, sys as _ng_sys  # N-Hack 専用の門（下の3行を消すとこのキットは動きません）
_ng_sys.path.insert(0, _ng_os.path.dirname(_ng_os.path.abspath(__file__)))
import nhack_gate as _nhack_gate  # noqa: E402,F401


import argparse
import re
import sys
import time

import th
from _common import ApiError, append_log, read_text_arg

LIMIT = 500


def parse_md(md: str) -> tuple[list[str], dict]:
    meta = {"topic": None, "images": []}
    for m in re.finditer(r"^- (topic|image):\s*(\S.*)$", md, re.M):
        if m.group(1) == "topic":
            meta["topic"] = m.group(2).strip()
        else:
            meta["images"].append(m.group(2).strip())
    parts = re.split(r"^## \d+投稿目\s*$", md, flags=re.M)[1:]
    clean = []
    for x in parts:
        x = re.sub(r"^- (topic|image):.*$", "", x, flags=re.M)
        x = re.sub(r"^<!--.*?-->$", "", x, flags=re.M | re.S)
        clean.append(x.strip())
    return [x for x in clean if x], meta


def is_emoji(c: str) -> bool:
    o = ord(c)
    return o >= 0x1F000 or 0x2600 <= o <= 0x27BF or o in (0xFE0F, 0x200D)


def count(text: str) -> int:
    """公式の数え方の近似：ふつうの文字は1字、絵文字は UTF-8 のバイト数。"""
    return sum(len(c.encode("utf-8")) if is_emoji(c) else 1 for c in text)


def check(parts: list[str], topic: str | None) -> None:
    errs = []
    if not parts:
        errs.append("本文がありません")
    if len(parts) > 10:
        errs.append(f"ツリーが {len(parts)} 本（このキットは10本まで）")
    for i, t in enumerate(parts, 1):
        n = count(t)
        if n > LIMIT:
            errs.append(f"{i}投稿目が {n} 字（上限 {LIMIT}・絵文字はバイト数で数える）")
        if re.search(r"https?://", t) and i == 1:
            print("  注意: 1投稿目にURLがあります（伸びにくい傾向。リンクは続きかプロフィールへ）")
        if re.search(r"(?<!\S)#\S+", t):
            print(f"  注意: {i}投稿目に#があります（Threads はトピック1つ。--topic を使う）")
    if topic and (len(topic) > 50 or "." in topic or "&" in topic):
        errs.append("トピックは1〜50字・「.」「&」なし")
    if errs:
        sys.exit("[止めました] " + " ／ ".join(errs))


def quota(go: bool) -> None:
    _, uid, _ = th.base(go)
    try:
        r = th.get(f"{uid}/threads_publishing_limit",
                   {"fields": "quota_usage,config,reply_quota_usage,reply_config"}, go)
    except ApiError as e:
        print(f"  （投稿数の確認はできませんでした：{e.status}）")
        return
    if r and r.get("data"):
        d = r["data"][0]
        total = (d.get("config") or {}).get("quota_total")
        print(f"  直近24時間 投稿 {d.get('quota_usage')}／{total}　返信 {d.get('reply_quota_usage')}／{(d.get('reply_config') or {}).get('quota_total')}")
        if total and d.get("quota_usage", 0) >= total:
            sys.exit("[止めました] 24時間の投稿の上限です。")


def create_and_publish(params: dict, go: bool, wait: int) -> str:
    _, uid, _ = th.base(go)
    r = th.post(f"{uid}/threads", params, go)
    cid = (r or {}).get("id", "<入れ物のID>")
    if go:
        time.sleep(wait)
        for _ in range(5):
            s = th.get(cid, {"fields": "status,error_message"}, go) or {}
            if s.get("status") in ("FINISHED", "PUBLISHED", None):
                break
            if s.get("status") in ("ERROR", "EXPIRED"):
                sys.exit(f"[止めました] {s.get('status')}: {s.get('error_message')}")
            time.sleep(60)
    r = th.post(f"{uid}/threads_publish", {"creation_id": cid}, go)
    return (r or {}).get("id", "<公開した投稿のID>")


def post(parts: list[str], go: bool, topic: str | None = None, images: list[str] | None = None,
         wait: int = 30) -> list[str]:
    check(parts, topic)
    quota(go)
    _, uid, _ = th.base(go)
    ids: list[str] = []
    for i, text in enumerate(parts):
        params: dict = {"text": text}
        if i == 0 and topic:
            params["topic_tag"] = topic
        if i == 0 and images:
            if len(images) == 1:
                params.update({"media_type": "VIDEO" if images[0].lower().endswith((".mp4", ".mov")) else "IMAGE",
                               ("video_url" if images[0].lower().endswith((".mp4", ".mov")) else "image_url"): images[0]})
            else:
                if not 2 <= len(images) <= 20:
                    sys.exit("カルーセルは2〜20枚です。")
                kids = []
                for u in images:
                    is_v = u.lower().endswith((".mp4", ".mov"))
                    r = th.post(f"{uid}/threads", {"media_type": "VIDEO" if is_v else "IMAGE",
                                                   ("video_url" if is_v else "image_url"): u,
                                                   "is_carousel_item": "true"}, go)
                    kids.append((r or {}).get("id", "<子のID>"))
                params.update({"media_type": "CAROUSEL", "children": ",".join(kids)})
        else:
            params["media_type"] = "TEXT"
        if ids:
            params["reply_to_id"] = ids[-1]
        mid = create_and_publish(params, go, wait)
        ids.append(mid)
        print(f"  {i + 1}投稿目 → {mid}")
    if go:
        link = th.get(ids[0], {"fields": "permalink,timestamp"}, go) or {}
        append_log("published.jsonl", {"ids": ids, "permalink": link.get("permalink"),
                                       "timestamp": link.get("timestamp"), "head": parts[0][:40]})
        print(f"投稿しました: {link.get('permalink')}")
    else:
        print("\n（dry-run でした。本当に投稿するときは --go を付けます）")
    return ids


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--text")
    p.add_argument("--file")
    p.add_argument("--topic")
    p.add_argument("--image", action="append")
    p.add_argument("--wait", type=int, default=30, help="作ってから公開まで待つ秒（公式のすすめは平均30秒）")
    p.add_argument("--go", action="store_true")
    a = p.parse_args()
    if a.file:
        parts, meta = parse_md(read_text_arg(None, a.file))
    else:
        parts, meta = [read_text_arg(a.text, None)], {"topic": None, "images": []}
    post(parts, a.go, a.topic or meta["topic"], a.image or meta["images"], a.wait)


if __name__ == "__main__":
    main()
