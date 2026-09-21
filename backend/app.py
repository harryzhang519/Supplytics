"""
Supply Chain Resilience Agent — Flask Intelligence Hub.
Entry point: registers all route blueprints, initializes simulators, seeds demo data.
"""

import logging
import os

from flask import Flask
from flask_cors import CORS

from routes.disruption import disruption_bp
from routes.disruption_stream import disruption_stream_bp

from routes.feedback import feedback_bp
from routes.graph import graph_bp
from routes.suppliers import suppliers_bp
from routes.actions import actions_bp
from routes.settings import settings_bp
from routes.simulate import simulate_bp
from routes.safety import safety_bp
from routes.cron import cron_bp
from data.seed import seed_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)

    # ── CORS ──────────────────────────────────────────────────────────
    # Allow local frontend dev servers and any production origin.
    CORS(
        app,
        resources={r"/*": {"origins": ["http://localhost:5173", "http://localhost:3000", "*"]}},
        supports_credentials=True,
    )

    # Register blueprints
    app.register_blueprint(disruption_bp)
    app.register_blueprint(disruption_stream_bp)

    app.register_blueprint(feedback_bp)
    app.register_blueprint(graph_bp)
    app.register_blueprint(suppliers_bp)
    app.register_blueprint(actions_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(simulate_bp, url_prefix="/api")
    app.register_blueprint(safety_bp, url_prefix="/api")
    app.register_blueprint(cron_bp, url_prefix="/api/cron")

    # Health check
    @app.route("/api/health", methods=["GET"])
    def health():
        from services.gemini_service import is_gemini_available
        return {
            "status": "ok",
            "service": "Supply Chain Resilience Agent",
            "mode": "local",
            "gemini_live": is_gemini_available(),
        }

    # Seed demo data on startup — non-fatal if it fails
    logger.info("🌱 Seeding demo supply chain data...")
    try:
        seed_all()
        logger.info("✅ Seed complete: 8 suppliers, 7 sub-suppliers, 6 regions, 12 components, 4 products, 3 lessons")
    except Exception as exc:
        logger.warning(f"⚠️  Seed step failed (non-fatal): {exc}")

    return app


# Expose WSGI application for production Gunicorn server
app = create_app()

if __name__ == "__main__":
    from config import PORT
    logger.info(f"🚀 Starting Intelligence Hub on http://127.0.0.1:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=True)
