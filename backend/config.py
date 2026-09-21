"""Configuration constants for the Supply Chain Resilience Agent."""
import os
from dotenv import load_dotenv

# Load .env from backend directory (works regardless of CWD)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# ── GCP Configuration ────────────────────────────────────────────────
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "htf-sco")
GCP_REGION = os.getenv("GCP_REGION", "us-east1")
FIRESTORE_DATABASE = os.getenv("FIRESTORE_DATABASE", "htf-sco")

# ── Service Toggle ───────────────────────────────────────────────────
# Default to LOCAL simulators — set to 'true' only when GCP credentials are active.
USE_REAL_VERTEX = os.getenv("USE_REAL_VERTEX", "false").lower() == "true"
USE_REAL_FIRESTORE = os.getenv("USE_REAL_FIRESTORE", "false").lower() == "true"
USE_REAL_SPANNER = os.getenv("USE_REAL_SPANNER", "false").lower() == "true"

# ── Local Development ────────────────────────────────────────────────
# Optional Gemini REST API key (google-generativeai package)
# Leave empty to use the built-in simulator templates.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
USE_LOCAL_STORAGE = os.getenv("USE_LOCAL_STORAGE", "true").lower() == "true"
PORT = int(os.getenv("PORT", "5000"))

# ── AI Model Configuration ───────────────────────────────────────────
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
EMBEDDING_DIM = 768 if USE_REAL_VERTEX else 256

# ── Business Logic ───────────────────────────────────────────────────
DEFAULT_RISK_APPETITE = "balanced"  # conservative | balanced | aggressive
REVENUE_AT_RISK_THRESHOLD = 500000  # USD — triggers executive escalation
CONFIDENCE_THRESHOLD = 70  # % — below this requires manual review
DEFAULT_SLA_PENALTY_PER_DAY = 2500  # USD per day late
EXPEDITED_SHIPPING_MULTIPLIER = 2.8  # cost multiplier for rush orders

# Health score weights
HEALTH_WEIGHTS = {
    "on_time_delivery": 0.40,
    "quality_score": 0.25,
    "news_sentiment": 0.20,
    "financial_stability": 0.15,
}

# Agent risk appetite multipliers
RISK_APPETITE_PROFILES = {
    "conservative": {"cost_weight": 2.0, "speed_weight": 0.5},
    "balanced": {"cost_weight": 1.0, "speed_weight": 1.0},
    "aggressive": {"cost_weight": 0.5, "speed_weight": 2.0},
}
