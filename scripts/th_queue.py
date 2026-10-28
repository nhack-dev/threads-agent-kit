"""予約投稿（API に予約の機能は無いので、このキットが時刻を見て出す）。

  python3 scripts/th_queue.py add --at "2026-11-01 08:00" --file drafts/2026-11-01-0800.md
  python3 scripts/th_queue.py list
  python3 scripts/th_queue.py run          # 時刻が来たものを表示するだけ
  python3 scripts/th_queue.py run --go     # 本当に投稿（5〜10分おきに動かす）

1回の run で出すのは2本まで（まとめて出しすぎない）。投稿したものは queue/done/ へ。
"""
from __future__ import annotations

import os as _ng_os, sys as _ng_sys  # N-Hack 専用の門（下の3行を消すとこのキットは動きません）
_ng_sys.path.insert(0, _ng_os.path.dirname(_ng_os.path.abspath(__file__)))
import nhack_gate as _nhack_gate  # noqa: E402,F401


import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from _common import ROOT, read_text_arg

Q = ROOT / "queue"
DONE = Q / "done"
FMT = "%Y-%m-%d %H:%M"


def items() -> list[Path]:
    return sorted(Q.glob("*.json"))


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("add")
    s.add_argument("--at", required=True)
    s.add_argument("--file", required=True)
    sub.add_parser("list")
    r = sub.add_parser("run")
    r.add_argument("--go", action="store_true")
    a = p.parse_args()

    if a.cmd == "add":
        at = datetime.strptime(a.at, FMT)
        Q.mkdir(exist_ok=True)
        f = Q / f"{at.strftime('%Y%m%d-%H%M')}.json"
        if f.exists():
            sys.exit(f"同じ時刻の予約があります: {f.name}")
        f.write_text(json.dumps({"at": at.strftime(FMT), "file": a.file}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"予約しました: {f.relative_to(ROOT)}")
    elif a.cmd == "list":
        for x in items():
            it = json.loads(x.read_text(encoding="utf-8"))
            print(f"{it['at']}  {it['file']}")
        print(f"予約 {len(items())} 件")
    else:
        from th_post import parse_md, post
        now = datetime.now()
        due = [x for x in items() if datetime.strptime(json.loads(x.read_text())["at"], FMT) <= now]
        if not due:
            print("時刻が来た予約はありません。")
            return
        for x in due[:2]:
            it = json.loads(x.read_text(encoding="utf-8"))
            print(f"→ {x.name}")
            parts, meta = parse_md(read_text_arg(None, it["file"]))
            ids = post(parts, a.go, meta["topic"], meta["images"])
            if a.go:
                DONE.mkdir(parents=True, exist_ok=True)
                it["ids"] = ids
                (DONE / x.name).write_text(json.dumps(it, ensure_ascii=False, indent=2), encoding="utf-8")
                x.unlink()
                time.sleep(5)


if __name__ == "__main__":
    main()
