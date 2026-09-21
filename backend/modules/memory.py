"""
Memory & Reflection System — Lesson storage, retrieval, and continuous improvement.
Uses Firestore for persistent memory and similarity search for context injection.
"""

from services.firestore_factory import firestore_db
from services.vertex_simulator import vertex_ai


def store_lesson(strategy_id, strategy_summary, context, rating=None, actual_outcome=None):
    """Store a strategy outcome as a lesson in Firestore with embedding."""
    embedding = vertex_ai.generate_embedding(strategy_summary)

    doc_id = firestore_db.add_document("lessons", {
        "strategy_id": strategy_id,
        "summary": strategy_summary,
        "context": context,
        "rating": rating,
        "actual_outcome": actual_outcome,
        "embedding": embedding,
        "status": "active",
    })

    return doc_id


def retrieve_relevant_lessons(query, top_k=3):
    """Find past lessons similar to current situation via embedding similarity."""
    query_embedding = vertex_ai.generate_embedding(query)
    results = firestore_db.similarity_search(query_embedding, "lessons", top_k=top_k)
    return results


def format_lessons_for_context(lessons):
    """Format retrieved lessons as prompt context for Gemini."""
    if not lessons:
        return "No relevant past lessons found."

    lines = ["## Relevant Past Lessons\n"]
    for i, lesson in enumerate(lessons, 1):
        doc = lesson["document"]
        similarity = lesson["similarity"]
        rating_str = f" (Rated: {doc['rating']}/5)" if doc.get("rating") else ""
        outcome_str = f"\n   Actual Outcome: {doc['actual_outcome']}" if doc.get("actual_outcome") else ""

        lines.append(
            f"### Lesson #{doc['id']}{rating_str} (Relevance: {similarity:.0%})\n"
            f"   Strategy: {doc.get('summary', 'N/A')}\n"
            f"   Context: {doc.get('context', 'N/A')}{outcome_str}\n"
        )

    return "\n".join(lines)


def store_feedback(strategy_id, rating, comment=None, actual_outcome=None):
    """Store user feedback on a strategy, and optionally update the lesson."""
    # Store feedback record
    doc_id = firestore_db.add_document("feedback", {
        "strategy_id": strategy_id,
        "rating": rating,
        "comment": comment,
        "actual_outcome": actual_outcome,
    })

    # Also update the lesson record if it exists
    lessons = firestore_db.query("lessons", {"strategy_id": strategy_id})
    for lesson in lessons:
        update = {"rating": rating}
        if actual_outcome:
            update["actual_outcome"] = actual_outcome
        if comment:
            update["feedback_comment"] = comment
        firestore_db.update_document("lessons", lesson["id"], update)

    return doc_id


def reflect_on_outcomes():
    """
    Continuous Improvement — Analyze negative feedback patterns
    and return persona prompt adjustments.
    Scans for ≤2 star feedback and identifies recurring issues.
    """
    all_feedback = firestore_db.get_all("feedback")
    negative = [f for f in all_feedback if f.get("rating", 3) <= 2]

    if not negative:
        return {
            "adjustments": [],
            "summary": "No negative feedback patterns detected. Agents performing well.",
            "negative_count": 0,
            "total_count": len(all_feedback),
        }

    # Analyze patterns in negative feedback
    cost_related = []
    speed_related = []
    for fb in negative:
        comment = (fb.get("comment", "") or "").lower()
        outcome = (fb.get("actual_outcome", "") or "").lower()
        text = comment + " " + outcome

        if any(w in text for w in ["cost", "expensive", "overbudget", "over budget", "price", "margin"]):
            cost_related.append(fb)
        if any(w in text for w in ["slow", "late", "delay", "time", "deadline"]):
            speed_related.append(fb)

    adjustments = []
    if len(cost_related) >= 2:
        adjustments.append({
            "agent": "finance_agent",
            "adjustment": "Increase cost estimation buffers by 15%. Prioritize cost-conservative options.",
            "reason": f"{len(cost_related)} instances of cost overrun feedback detected.",
        })
    if len(speed_related) >= 2:
        adjustments.append({
            "agent": "logistics_agent",
            "adjustment": "Reduce lead-time estimates by 10%. Prioritize faster reroute options.",
            "reason": f"{len(speed_related)} instances of speed-related negative feedback detected.",
        })

    return {
        "adjustments": adjustments,
        "summary": f"Analyzed {len(negative)} negative feedback entries. {len(adjustments)} adjustment(s) recommended.",
        "negative_count": len(negative),
        "total_count": len(all_feedback),
    }
