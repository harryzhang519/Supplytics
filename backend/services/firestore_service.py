"""
Firestore Service — Real Google Cloud Firestore integration.
Provides document storage for lessons, feedback, and settings.
Uses client-side cosine similarity for embedding search (small dataset).
"""

import uuid
import math
import time
import logging
from google.cloud import firestore
from config import GCP_PROJECT_ID, FIRESTORE_DATABASE

logger = logging.getLogger(__name__)


class FirestoreService:
    """Real Cloud Firestore client with cosine similarity search."""

    def __init__(self):
        self.db = firestore.Client(project=GCP_PROJECT_ID, database=FIRESTORE_DATABASE)
        # Probe the database to trigger auth errors early (non-fatal)
        try:
            list(self.db.collection("health_check").limit(1).stream())
            logger.info(f"✅ Firestore initialized — project={GCP_PROJECT_ID}")
        except Exception as e:
            logger.warning(
                f"⚠️  Firestore health-check probe failed ({type(e).__name__}: {e}). "
                "The client was created but may not have access."
            )
            # Re-raise so firestore_factory can catch it and fall back to simulator
            raise

    def add_document(self, collection, data, doc_id=None):
        """Add a document to a collection. Returns the document ID."""
        doc_id = doc_id or str(uuid.uuid4())[:8]
        doc_data = {
            "id": doc_id,
            "created_at": time.time(),
            **data,
        }
        self.db.collection(collection).document(doc_id).set(doc_data)
        return doc_id

    def get_document(self, collection, doc_id):
        """Get a single document by ID."""
        doc = self.db.collection(collection).document(doc_id).get()
        if doc.exists:
            return doc.to_dict()
        return None

    def update_document(self, collection, doc_id, data):
        """Update fields in an existing document."""
        data["updated_at"] = time.time()
        self.db.collection(collection).document(doc_id).update(data)
        return self.get_document(collection, doc_id)

    def query(self, collection, filters=None):
        """Query documents with equality filters: {field: value}."""
        ref = self.db.collection(collection)
        if filters:
            for field, value in filters.items():
                ref = ref.where(field, "==", value)
        docs = ref.stream()
        return [doc.to_dict() for doc in docs]

    def get_all(self, collection):
        """Get all documents in a collection."""
        docs = self.db.collection(collection).stream()
        return [doc.to_dict() for doc in docs]

    def similarity_search(self, query_embedding, collection, top_k=3):
        """
        Cosine similarity search on documents with 'embedding' field.
        Client-side computation — suitable for small datasets (<1000 docs).
        """
        docs = self.get_all(collection)
        results = []
        for doc in docs:
            emb = doc.get("embedding")
            if emb:
                sim = self._cosine_similarity(query_embedding, emb)
                safe_doc = {k: v for k, v in doc.items() if k != "embedding"}
                results.append({"document": safe_doc, "similarity": sim})
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    @staticmethod
    def _cosine_similarity(a, b):
        """Cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
