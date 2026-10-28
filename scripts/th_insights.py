"""数字を取る（投稿ごと・アカウント全体）→ data/ に CSV と JSON。

  python3 scripts/th_insights.py --limit 50 --go

投稿ごと（公式の名前）：views likes replies reposts quotes shares
アカウント：views likes replies reposts quotes clicks followers_count
（views と shares は公式で「開発中」と書かれています。0 のままのことがあります）
"""
from __future__ import annotations

import os as _ng_os, sys as _ng_sys  # N-Hack 専用の門（下の3行を消すとこのキットは動きません）
_ng_sys.path.insert(0, _ng_os.path.dirname(_ng_os.path.abspath(__file__)))
import nhack_gate as _nhack_gate  # noqa: E402,F401


import argparse
import csv
import time

import th
from _common import DATA, ApiError, save_json, today

POST = ["views", "likes", "replies", "reposts", "quotes", "shares"]
USER = ["views", "likes", "replies", "reposts", "quotes", "clicks", "followers_count"]


def val(d: dict):
    if "total_value" in d:
        return (d["total_value"] or {}).get("value")
    vs = d.get("values") or []
    return sum(v.get("value", 0) for v in vs) if len(vs) > 1 else (vs[0].get("value") if vs else None)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--days", type=int, default=7, help="アカウント全体を何日分見るか")
    p.add_argument("--go", action="store_true")
    a = p.parse_args()
    _, uid, _ = th.base(a.go)

    r = th.get("me/threads", {"fields": "id,text,timestamp,permalink,media_type,is_quote_post,topic_tag",
                              "limit": str(min(a.limit, 100))}, a.go)
    if not a.go:
        th.get("<MEDIA_ID>/insights", {"metric": ",".join(POST)}, a.go)
        now = int(time.time())
        th.get(f"{uid}/threads_insights", {"metric": ",".join(USER), "since": str(now - a.days * 86400),
                                           "until": str(now)}, a.go)
        print("\n（dry-run でした。--go で取ります）")
        return

    rows = []
    for m in (r or {}).get("data", []):
        if m.get("media_type") == "REPOST_FACADE":
            continue
        try:
            x = th.get(f"{m['id']}/insights", {"metric": ",".join(POST)}, a.go) or {}
            vals = {d["name"]: val(d) for d in x.get("data", [])}
        except ApiError:
            vals = {}
        text = (m.get("text") or "")
        rows.append({"id": m["id"], "timestamp": m.get("timestamp"), "permalink": m.get("permalink"),
                     "topic": m.get("topic_tag"), "chars": len(text), "head": text.splitlines()[0][:40] if text else "",
                     **{k: vals.get(k) for k in POST}})
        time.sleep(0.3)

    now = int(time.time())
    acct = {}
    for n in USER:
        params = {"metric": n}
        if n != "followers_count":
            params.update({"since": str(now - a.days * 86400), "until": str(now)})
        try:
            x = th.get(f"{uid}/threads_insights", params, a.go) or {}
            acct[n] = val(x["data"][0]) if x.get("data") else None
        except ApiError:
            acct[n] = None

    DATA.mkdir(exist_ok=True)
    path = DATA / f"insights-{today()}.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "timestamp", "permalink", "topic", "chars", "head"] + POST)
        w.writeheader()
        w.writerows(rows)
    save_json(f"account-{today()}.json", {f"last_{a.days}_days": acct})
    print(f"投稿 {len(rows)} 本 → data/{path.name}")
    print("アカウント:", acct)


if __name__ == "__main__":
    main()
