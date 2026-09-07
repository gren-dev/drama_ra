import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def _get(key: str, default: str = "") -> str:
    """优先 .env / 环境变量（本地、GitHub Actions），其次 Streamlit Cloud 的 st.secrets。"""
    v = os.getenv(key)
    if v:
        return v
    try:
        import streamlit as st
        return str(st.secrets.get(key, default) or default)
    except Exception:
        return default


DATABASE_URL = _get("DATABASE_URL", f"sqlite:///{ROOT/'data'/'radar.db'}")
SNAPSHOT_DIR = ROOT / "data" / "snapshots"
TAXONOMY_PATH = ROOT / "taxonomy.yaml"

LLM_PROVIDER = _get("LLM_PROVIDER", "mock")
ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = _get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
OPENAI_COMPAT_BASE_URL = _get("OPENAI_COMPAT_BASE_URL")
OPENAI_COMPAT_API_KEY = _get("OPENAI_COMPAT_API_KEY")
OPENAI_COMPAT_MODEL = _get("OPENAI_COMPAT_MODEL", "deepseek-chat")
REPORT_MODEL = _get("REPORT_MODEL") or None

HTTP_PROXY = _get("HTTP_PROXY") or None
CRAWL_INTERVAL_HOURS = int(_get("CRAWL_INTERVAL_HOURS", "4"))

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
]
