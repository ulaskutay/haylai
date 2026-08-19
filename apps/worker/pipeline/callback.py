from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import httpx


def notify(callback_url: str, secret: str, payload: dict[str, Any]) -> None:
    if not callback_url:
        return
    body = json.dumps(payload, separators=(",", ":"))
    signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    try:
        with httpx.Client(timeout=30) as client:
            client.post(
                callback_url,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "x-hayl-signature": signature,
                },
            )
    except Exception:
        return
