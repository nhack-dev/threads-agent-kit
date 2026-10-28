"""共通の小道具（標準ライブラリだけ）。

- .env を読む
- API を呼ぶ（--go が無いときは「呼ぶ予定のリクエスト」を表示するだけ）
- 鍵は表示しない（伏せ字にする）
"""
from __future__ import annotations

import os as _ng_os, sys as _ng_sys  # N-Hack 専用の門（下の3行を消すとこのキットは動きません）
_ng_sys.path.insert(0, _ng_os.path.dirname(_ng_os.path.abspath(__file__)))
import nhack_gate as _nhack_gate  # noqa: E402,F401


import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SECRET_KEYS = ("access_token", "client_secret", "password", "refresh_token", "code")


def load_env() -> None:
    """ROOT/.env を読んで環境変数に入れる（すでにある値は上書きしない）。"""
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def env(key: str, go: bool, default: str | None = None) -> str:
    """値を取る。dry-run なら無くても仮の値で進める。本番（--go）なら止める。"""
    val = os.environ.get(key) or default
    if val:
        return val
    if go:
        sys.exit(f"[止めました] .env に {key} がありません。README の「キーの取り方」を見てください。")
    return f"<{key}>"


def mask(value) -> str:
    s = str(value)
    if s.startswith("<") and s.endswith(">"):
        return s
    return s[:4] + "…(伏せ字)" if len(s) > 8 else "(伏せ字)"


def _masked(params: dict | None) -> dict:
    if not params:
        return {}
    return {k: (mask(v) if k in SECRET_KEYS else v) for k, v in params.items()}


def show(method: str, url: str, params: dict | None = None, body: dict | None = None,
         headers: dict | None = None) -> None:
    print(f"[dry-run] {method} {url}")
    if params:
        print("          params:", json.dumps(_masked(params), ensure_ascii=False))
    if body:
        print("          body:  ", json.dumps(_masked(body), ensure_ascii=False)[:600])
    if headers and "Authorization" in headers:
        print("          header: Authorization: Bearer (伏せ字)")


def call(method: str, url: str, params: dict | None = None, body: dict | None = None,
         headers: dict | None = None, go: bool = False, json_body: bool = False,
         retries: int = 2):
    """API を1回呼ぶ。go=False なら表示だけして None を返す。

    GET は params をクエリに、POST は params をフォームで送る（json_body=True なら body を JSON で）。
    """
    if not go:
        show(method, url, params, body, headers)
        return None
    headers = dict(headers or {})
    headers.setdefault("User-Agent", "sns-agent-kit/1.0")
    q = ""
    data = None
    if method == "GET" or (method == "DELETE" and params):
        q = "?" + urllib.parse.urlencode(params or {})
    elif json_body:
        if params:
            q = "?" + urllib.parse.urlencode(params)
        data = json.dumps(body or {}).encode("utf-8")
        headers["Content-Type"] = "application/json"
    else:
        data = urllib.parse.urlencode({**(params or {}), **(body or {})}).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url + q, data=data, method=method, headers=headers)
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")
            if e.code in (429, 500, 502, 503) and attempt < retries:
                wait = 30 * (attempt + 1)
                print(f"[待ちます] HTTP {e.code}。{wait}秒後にもう一度だけ試します。")
                time.sleep(wait)
                continue
            raise ApiError(e.code, detail) from None
        except urllib.error.URLError as e:
            if attempt < retries:
                time.sleep(10)
                continue
            raise ApiError(0, str(e)) from None


class ApiError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(f"HTTP {status}: {detail[:800]}")
        self.status = status
        self.detail = detail


def save_json(name: str, obj) -> Path:
    DATA.mkdir(exist_ok=True)
    p = DATA / name
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def append_log(name: str, row: dict) -> None:
    DATA.mkdir(exist_ok=True)
    with (DATA / name).open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_log(name: str) -> list[dict]:
    p = DATA / name
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def today() -> str:
    return time.strftime("%Y%m%d")


def read_text_arg(text: str | None, file: str | None) -> str:
    if file:
        p = Path(file)
        if not p.exists():
            p = ROOT / file
        return p.read_text(encoding="utf-8").strip()
    return (text or "").strip()
