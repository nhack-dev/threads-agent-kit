"""Threads のトークンを作る・延ばす。

  python3 scripts/th_auth.py url                 # ログイン用のURLを出す（ブラウザで開く）
  python3 scripts/th_auth.py code <コード> --go   # 戻ってきたURLの code= の値 → 長期トークン（60日）
  python3 scripts/th_auth.py refresh --go        # 長期トークンを60日延ばす（発行から24時間たってから）

アプリの管理画面の「ユーザートークン生成ツール」で作る方法もあります（README）。
新しいトークンは画面に出すだけです。.env の TH_ACCESS_TOKEN を自分で書き換えてください。
"""

import os as _ng_os, sys as _ng_sys  # N-Hack 専用の門（下の3行を消すとこのキットは動きません）
_ng_sys.path.insert(0, _ng_os.path.dirname(_ng_os.path.abspath(__file__)))
import nhack_gate as _nhack_gate  # noqa: E402,F401

import argparse
import json
import sys
import urllib.parse

from _common import call, env, load_env
from th import root

load_env()
SCOPES = "threads_basic,threads_content_publish,threads_manage_replies,threads_read_replies,threads_manage_insights,threads_keyword_search"

p = argparse.ArgumentParser()
p.add_argument("action", choices=["url", "code", "refresh"])
p.add_argument("value", nargs="?")
p.add_argument("--go", action="store_true")
a = p.parse_args()

if a.action == "url":
    q = {"client_id": env("TH_APP_ID", False), "redirect_uri": env("TH_REDIRECT_URI", False),
         "scope": SCOPES, "response_type": "code"}
    print("このURLをブラウザで開き、許可してください：")
    print("https://threads.com/oauth/authorize?" + urllib.parse.urlencode(q))
    print("\n戻ってきたURLの code= の後ろ（最後の #_ は外す）を、次のコマンドに貼ります：")
    print("python3 scripts/th_auth.py code <コード> --go")
elif a.action == "code":
    code = (a.value or "<CODE>").split("#")[0]
    r = call("POST", f"{root()}/oauth/access_token",
             body={"client_id": env("TH_APP_ID", a.go), "client_secret": env("TH_APP_SECRET", a.go),
                   "grant_type": "authorization_code", "redirect_uri": env("TH_REDIRECT_URI", a.go), "code": code},
             go=a.go)
    short = (r or {}).get("access_token", "<短期トークン>")
    r2 = call("GET", f"{root()}/access_token",
              {"grant_type": "th_exchange_token", "client_secret": env("TH_APP_SECRET", a.go), "access_token": short},
              go=a.go)
    if a.go and "access_token" not in (r2 or {}):
        sys.exit(f"[止めました] 長期トークンが返ってきませんでした: {r2}")
    if r2:
        print(json.dumps({"user_id": r.get("user_id"), "expires_in_days": int(r2.get("expires_in", 0)) // 86400}))
        print("長期トークン（.env の TH_ACCESS_TOKEN に貼る・人に見せない）:")
        print(r2["access_token"])
        print(f"TH_USER_ID={r.get('user_id')}")
else:
    r = call("GET", f"{root()}/refresh_access_token",
             {"grant_type": "th_refresh_token", "access_token": env("TH_ACCESS_TOKEN", a.go)}, go=a.go)
    if a.go and "access_token" not in (r or {}):
        sys.exit(f"[止めました] トークンが返ってきませんでした: {r}")
    if r:
        print(json.dumps({"expires_in_days": int(r.get("expires_in", 0)) // 86400}))
        print("新しいトークン:")
        print(r["access_token"])
