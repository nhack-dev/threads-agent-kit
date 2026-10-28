"""つながっているか確かめる。

  python3 scripts/th_whoami.py --go
"""

import os as _ng_os, sys as _ng_sys  # N-Hack 専用の門（下の3行を消すとこのキットは動きません）
_ng_sys.path.insert(0, _ng_os.path.dirname(_ng_os.path.abspath(__file__)))
import nhack_gate as _nhack_gate  # noqa: E402,F401

import argparse
import json

import th

p = argparse.ArgumentParser()
p.add_argument("--go", action="store_true")
a = p.parse_args()
r = th.get("me", {"fields": "id,username,threads_biography"}, a.go)
if r:
    print(json.dumps(r, ensure_ascii=False, indent=2))
    print("\n→ .env の TH_USER_ID には上の id を入れてください。")
