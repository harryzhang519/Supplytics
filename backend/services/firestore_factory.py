"""
Firestore factory — selects the real Firestore client or the simulator
based on the USE_REAL_FIRESTORE flag in config.py.

Both FirestoreService and FirestoreSimulator expose identical method signatures:
    add_document, get_document, update_document, query, get_all, similarity_search
so callers can import firestore_db from this module without any other changes.

On any auth/credential/permission error the factory silently falls back to the
in-memory simulator so the app always boots cleanly in local dev mode.
"""

import logging

from config import USE_REAL_FIRESTORE
from services.firestore_simulator import FirestoreSimulator

logger = logging.getLogger(__name__)

firestore_db = None  # resolved below

if USE_REAL_FIRESTORE:
    try:
        from services.firestore_service import FirestoreService
        firestore_db = FirestoreService()
        logger.info("✅ Using real Cloud Firestore")
    except Exception as e:
        logger.warning(
            f"⚠️  Could not connect to Cloud Firestore ({type(e).__name__}: {e}). "
            "Falling back to in-memory simulator."
        )
        firestore_db = FirestoreSimulator()
else:
    logger.info("ℹ️  USE_REAL_FIRESTORE=false — using in-memory Firestore simulator")
    firestore_db = FirestoreSimulator()
