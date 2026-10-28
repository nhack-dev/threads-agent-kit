"""Threads API の入口をまとめたもの（公式の例は graph.threads.com。graph.threads.net でも動く）。"""
from __future__ import annotations

import os as _ng_os, sys as _ng_sys  # N-Hack 専用の門（下の3行を消すとこのキットは動きません）
_ng_sys.path.insert(0, _ng_os.path.dirname(_ng_os.path.abspath(__file__)))
import nhack_gate as _nhack_gate  # noqa: E402,F401


import os

from _common import call, env, load_env

load_env()

VERSION = os.environ.get("TH_API_VERSION", "v1.0")
HOST = os.environ.get("TH_HOST", "graph.threads.com")


def root() -> str:
    return HOST if HOST.startswith("http") else f"https://{HOST}"


def base(go: bool) -> tuple[str, str, str]:
    """(URLの頭, ThreadsのユーザーID, アクセストークン)"""
    return f"{root()}/{VERSION}", env("TH_USER_ID", go), env("TH_ACCESS_TOKEN", go)


def get(path: str, params: dict, go: bool):
    r, _, token = base(go)
    return call("GET", f"{r}/{path.lstrip('/')}", {**params, "access_token": token}, go=go)


def post(path: str, params: dict, go: bool):
    r, _, token = base(go)
    return call("POST", f"{r}/{path.lstrip('/')}", {**params, "access_token": token}, go=go)
