"""キーワードで投稿を探す（リサーチ用）。

  python3 scripts/th_search.py "家計簿" --go
  python3 scripts/th_search.py "家計簿" --recent --go

公式の決まり：
- 権限 threads_keyword_search が要る
- この権限の審査が通るまでは、自分の投稿しか出てこない（審査後は公開の投稿）
- 1人あたり24時間で2200回まで（同じ言葉でも数える・0件の検索は数えない）
結果は data/search-<日付>.jsonl に足していきます。他人の文をそのまま使わず「型」だけ見ます。
"""

import os as _ng_os, sys as _ng_sys  # N-Hack 専用の門（下の3行を消すとこのキットは動きません）
_ng_sys.path.insert(0, _ng_os.path.dirname(_ng_os.path.abspath(__file__)))
import nhack_gate as _nhack_gate  # noqa: E402,F401

import argparse
import time

import th
from _common import append_log

p = argparse.ArgumentParser()
p.add_argument("q")
p.add_argument("--recent", action="store_true", help="新しい順（既定は人気順）")
p.add_argument("--tag", action="store_true", help="トピックで探す")
p.add_argument("--limit", type=int, default=25)
p.add_argument("--go", action="store_true")
a = p.parse_args()

r = th.get("keyword_search", {"q": a.q, "search_type": "RECENT" if a.recent else "TOP",
                              "search_mode": "TAG" if a.tag else "KEYWORD", "limit": str(min(a.limit, 100)),
                              "fields": "id,text,timestamp,permalink,topic_tag,media_type"}, a.go)
if r:
    for m in r.get("data", []):
        append_log(f"search-{time.strftime('%Y%m%d')}.jsonl", {"q": a.q, **m})
        print(f"- {(m.get('text') or '').splitlines()[0][:60] if m.get('text') else ''}  {m.get('permalink')}")
    print(f"{len(r.get('data', []))} 件（data/search-{time.strftime('%Y%m%d')}.jsonl に足しました）")
