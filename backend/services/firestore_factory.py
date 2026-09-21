"""
Firestore factory — selects the real Firestore client or the simulator
based on the USE_REAL_FIRESTORE flag in config.py.

Both FirestoreService and firestore_simulator expose identical method signatures:
    add_document, get_document, update_document, query, get_all, similarity_search
so callers can import firestore_db from this module without any other changes.
"""

from config import USE_REAL_FIRESTORE

if USE_REAL_FIRESTORE:
    from services.firestore_service import FirestoreService
    firestore_db = FirestoreService()
else:
    from services.firestore_simulator import firestore_db
