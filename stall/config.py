"""Environment for local runs. Reads the process env, then .env."""

from __future__ import annotations

import os
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

DEFAULTS = {
    "STALL_URL": "http://localhost:8000",
    "LLM_BASE_URL": "https://generativelanguage.googleapis.com/v1beta/openai",
    "LLM_MODEL": "gemini-3.1-flash-lite",
}


def load() -> dict:
    env_file = REPO_ROOT / ".env"
    file_vars = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                file_vars[key.strip()] = value.strip()
    cfg = {}
    for key in ("STALL_URL", "LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY",
                "EMBEDDING_BASE_URL", "EMBEDDING_MODEL"):
        cfg[key] = os.environ.get(key) or file_vars.get(key) or DEFAULTS.get(key, "")
    cfg["STALL_URL"] = cfg["STALL_URL"].rstrip("/")
    cfg["LLM_BASE_URL"] = cfg["LLM_BASE_URL"].rstrip("/")
    cfg["EMBEDDING_BASE_URL"] = cfg["EMBEDDING_BASE_URL"].rstrip("/")
    return cfg
