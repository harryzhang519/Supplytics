"""POST /api/action/approve — Approve or reject a suggested action."""

from flask import Blueprint, request, jsonify
import time
from services.firestore_factory import firestore_db

actions_bp = Blueprint("actions", __name__)

# In-memory action store (in production, this would be in Spanner or Firestore)
action_store = {}


@actions_bp.route("/api/action/approve", methods=["POST"])
def approve_action():
    data = request.get_json()
    action_id = data.get("action_id", "")
    approved = data.get("approved", True)
    action_type = data.get("type", "unknown")

    if not action_id:
        return jsonify({"error": "action_id is required"}), 400

    message = "Action approved and logged."
    if approved:
        if action_type == "erp_adjustment":
            message = "Safety stock levels updated in ERP."
        elif action_type == "po_draft_update" or action_type == "preemptive_stock_build":
            message = "Purchase Orders drafted in ERP."
        elif action_type == "supplier_email":
            message = "Email successfully dispatched to supplier."
    else:
        message = "Action rejected."

    action_store[action_id] = {
        "action_id": action_id,
        "status": "approved" if approved else "rejected",
        "type": action_type,
        "message": message
    }

    # Log to Firestore
    firestore_db.add_document("action_log", {
        "action_id": action_id,
        "status": "approved" if approved else "rejected",
        "type": action_type,
        "timestamp": time.time()
    })

    return jsonify({
        "success": True,
        "action_id": action_id,
        "status": "approved" if approved else "rejected",
        "message": message
    })


@actions_bp.route("/api/actions", methods=["GET"])
def get_actions():
    return jsonify({"actions": list(action_store.values())})
