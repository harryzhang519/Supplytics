"""
Gemini REST API Service — Optional live AI via google-generativeai.

Used as a lightweight upgrade path when GEMINI_API_KEY is set in .env.
Falls back gracefully to None on import error, missing key, or API failure
so the vertex_simulator templates always remain the safe default.

Usage (internal):
    from services.gemini_service import gemini_call
    result = gemini_call(prompt)  # returns str or None
"""

import logging
import json

logger = logging.getLogger(__name__)

# ── Try to import the google-generativeai package ─────────────────────
try:
    import google.generativeai as genai
    _SDK_AVAILABLE = True
except ImportError:
    genai = None
    _SDK_AVAILABLE = False
    logger.debug("google-generativeai not installed — Gemini REST mode unavailable")


def _get_client():
    """Return a configured Gemini GenerativeModel, or None if unavailable."""
    if not _SDK_AVAILABLE:
        return None
    from config import GEMINI_API_KEY, GEMINI_MODEL
    if not GEMINI_API_KEY or GEMINI_API_KEY in ("", "your_gemini_api_key_here"):
        return None
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        return genai.GenerativeModel(GEMINI_MODEL)
    except Exception as e:
        logger.warning(f"⚠️  Gemini client setup failed: {e}")
        return None


# Lazy singleton — only configured once per process
_client = None
_client_checked = False


def gemini_call(prompt: str, temperature: float = 0.4) -> str | None:
    """
    Send a prompt to the Gemini REST API and return the text response.

    Returns None on any failure so the caller can fall back to simulator.
    """
    global _client, _client_checked
    if not _client_checked:
        _client = _get_client()
        _client_checked = True

    if _client is None:
        return None

    try:
        response = _client.generate_content(
            prompt,
            generation_config={"temperature": temperature, "max_output_tokens": 2048},
        )
        text = response.text.strip()
        logger.debug(f"Gemini API response received ({len(text)} chars)")
        return text
    except Exception as e:
        logger.warning(f"⚠️  Gemini API call failed: {e} — will use simulator fallback")
        return None


def is_gemini_available() -> bool:
    """Return True if a live Gemini API key is configured and the SDK is installed."""
    global _client, _client_checked
    if not _client_checked:
        _client = _get_client()
        _client_checked = True
    return _client is not None
