"""届いた返信（リプ）を集めて、返事の下書きを作り、確かめたものだけ返す。

  python3 scripts/th_replies.py fetch --posts 10 --go   # data/reply-drafts.json に足す
  （エージェントが playbooks/05-replies.md の基準で reply を書き、approve を true にする）
  python3 scripts/th_replies.py send                    # 送る予定を見るだけ
  python3 scripts/th_replies.py send --go               # approve=true だけ返す（1回20件まで）
  python3 scripts/th_replies.py hide --reply-id 123 --go

公式の上限：返信は24時間で1000件まで。
"""
from __future__ import annotations

import os as _ng_os, sys as _ng_sys  # N-Hack 専用の門（下の3行を消すとこのキットは動きません）
_ng_sys.path.insert(0, _ng_os.path.dirname(_ng_os.path.abspath(__file__)))
import nhack_gate as _nhack_gate  # noqa: E402,F401


import argparse
import json
import time

import th
from _common import DATA, append_log, read_log
from th_post import count, create_and_publish

DRAFTS = DATA / "reply-drafts.json"


def load() -> list[dict]:
    return json.loads(DRAFTS.read_text(encoding="utf-8")) if DRAFTS.exists() else []


def store(rows: list[dict]) -> None:
    DATA.mkdir(exist_ok=True)
    DRAFTS.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch(n: int, go: bool) -> None:
    me = th.get("me", {"fields": "username"}, go) or {}
    posts = th.get("me/threads", {"fields": "id,text,timestamp", "limit": str(n)}, go)
    if not go:
        th.get("<MEDIA_ID>/conversation", {"fields": "id,text,username,timestamp,replied_to,hide_status"}, go)
        print("\n（dry-run でした）")
        return
    done = {r["reply_id"] for r in read_log("replied.jsonl")}
    rows = load()
    known = {r["reply_id"] for r in rows}
    added = 0
    for m in (posts or {}).get("data", []):
        r = th.get(f"{m['id']}/conversation", {"fields": "id,text,username,timestamp,replied_to,hide_status",
                                               "reverse": "false"}, go) or {}
        conv = r.get("data", [])
        answered = {(c.get("replied_to") or {}).get("id") for c in conv if c.get("username") == me.get("username")}
        for c in conv:
            if c.get("username") == me.get("username") or c["id"] in done or c["id"] in known or c["id"] in answered:
                continue
            if c.get("hide_status") not in (None, "NOT_HUSHED", "UNHUSHED"):
                continue
            rows.append({"reply_id": c["id"], "post": (m.get("text") or "")[:40], "from": c.get("username"),
                         "text": c.get("text"), "timestamp": c.get("timestamp"),
                         "reply": "", "approve": False, "note": ""})
            added += 1
        time.sleep(0.3)
    store(rows)
    print(f"新しい返信 {added} 件を data/reply-drafts.json に足しました")


def send(go: bool, wait: int) -> None:
    rows = load()
    todo = [r for r in rows if r.get("approve") and r.get("reply") and not r.get("sent")][:20]
    if not todo:
        print("送るものはありません（approve=true かつ reply があるものだけ）")
        return
    for r in todo:
        if count(r["reply"]) > 500:
            print(f"  飛ばしました（500字超え）: {r['reply_id']}")
            continue
        mid = create_and_publish({"media_type": "TEXT", "text": r["reply"], "reply_to_id": r["reply_id"]}, go, wait)
        if go:
            r["sent"] = True
            append_log("replied.jsonl", {"reply_id": r["reply_id"], "my_id": mid, "at": time.strftime("%Y-%m-%d %H:%M")})
            time.sleep(3)
    if go:
        store(rows)
        print(f"返信 {len(todo)} 件")
    else:
        print(f"\n（dry-run でした。返す予定 {len(todo)} 件）")


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--posts", type=int, default=10)
    f.add_argument("--go", action="store_true")
    s = sub.add_parser("send")
    s.add_argument("--wait", type=int, default=10)
    s.add_argument("--go", action="store_true")
    h = sub.add_parser("hide")
    h.add_argument("--reply-id", required=True)
    h.add_argument("--unhide", action="store_true")
    h.add_argument("--go", action="store_true")
    a = p.parse_args()
    if a.cmd == "fetch":
        fetch(a.posts, a.go)
    elif a.cmd == "send":
        send(a.go, a.wait)
    else:
        th.post(f"{a.reply_id}/manage_reply", {"hide": "false" if a.unhide else "true"}, a.go)
        print("非表示にしました（1段目の返信だけ非表示にできます）" if a.go else "（dry-run）")


if __name__ == "__main__":
    main()
