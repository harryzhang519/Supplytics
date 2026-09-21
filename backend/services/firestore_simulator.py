"""
Firestore Simulator — In-memory document store.
Simulates Cloud Firestore for lessons, feedback, and settings.
Drop-in replacement: swap for google.cloud.firestore to use real Firestore.
"""

import uuid
import math
import time


class FirestoreSimulator:
    """In-memory document database with similarity search via cosine distance."""

    def __init__(self):
        # collections[name][doc_id] = {fields}
        self.collections = {}

    def add_document(self, collection, data, doc_id=None):
        doc_id = doc_id or str(uuid.uuid4())[:8]
        if collection not in self.collections:
            self.collections[collection] = {}
        self.collections[collection][doc_id] = {
            "id": doc_id,
            "created_at": time.time(),
            **data,
        }
        return doc_id

    def get_document(self, collection, doc_id):
        return self.collections.get(collection, {}).get(doc_id)

    def update_document(self, collection, doc_id, data):
        doc = self.get_document(collection, doc_id)
        if doc:
            doc.update(data)
            doc["updated_at"] = time.time()
        return doc

    def query(self, collection, filters=None):
        """Simple query with equality filters: {field: value}."""
        docs = list(self.collections.get(collection, {}).values())
        if not filters:
            return docs
        results = []
        for doc in docs:
            match = all(doc.get(k) == v for k, v in filters.items())
            if match:
                results.append(doc)
        return results

    def get_all(self, collection):
        return list(self.collections.get(collection, {}).values())

    def similarity_search(self, query_embedding, collection, top_k=3):
        """Cosine similarity search on documents with 'embedding' field."""
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
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


# ── Singleton export ─────────────────────────────────────────────────
# Instantiated and exported by services/firestore_factory.py.
# Import firestore_db from there, not here.
firestore_db = FirestoreSimulator()
