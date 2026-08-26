"""Thin urllib client for the stall's HTTP API."""

from __future__ import annotations

import json
import urllib.error
import urllib.request


class StallError(Exception):
    pass


def _request(url: str, payload=None, timeout=60):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except urllib.error.URLError as e:
        raise StallError(
            f"cannot reach the stall at {url} — is STALL_URL right? ({e.reason})")


def get_text(url: str) -> str:
    status, body = _request(url)
    if status != 200:
        raise StallError(f"GET {url} -> {status}: {body[:200]!r}")
    return body.decode()


def get_json(url: str) -> dict:
    return json.loads(get_text(url))


def get_json_status(url: str) -> tuple[int, dict]:
    """For endpoints whose refusals are worth showing the student."""
    status, body = _request(url)
    try:
        return status, json.loads(body)
    except json.JSONDecodeError:
        raise StallError(f"GET {url} -> {status}: {body[:200]!r}")


def post_json(url: str, payload: dict, timeout: int = 60) -> tuple[int, dict]:
    status, body = _request(url, payload, timeout=timeout)
    try:
        return status, json.loads(body)
    except json.JSONDecodeError:
        raise StallError(f"POST {url} -> {status}: {body[:200]!r}")
