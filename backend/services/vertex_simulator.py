"""
Vertex AI Simulator — Simulated Gemini 1.5 Pro reasoning + Embeddings API.
Produces deterministic embeddings and structured AI responses without calling GCP.
Drop-in replacement: swap for vertexai.generative_models to use real Vertex AI.
"""

import hashlib
import math
import json
import random
from config import EMBEDDING_DIM


class VertexAISimulator:
    """Simulates Vertex AI Gemini 1.5 Pro and Embeddings API."""

    def generate_embedding(self, text):
        """
        Deterministic embedding from text hash.
        Same text always produces the same 256-dim vector (unit-normalized).
        """
        h = hashlib.sha256(text.lower().encode()).hexdigest()
        raw = []
        for i in range(EMBEDDING_DIM):
            chunk = h[(i * 2) % len(h): (i * 2) % len(h) + 2]
            val = (int(chunk, 16) - 128) / 128.0
            raw.append(val)
        # Normalize to unit vector
        norm = math.sqrt(sum(x * x for x in raw))
        if norm > 0:
            raw = [x / norm for x in raw]
        return raw

    def generate_response(self, prompt, persona=None, context=None):
        """
        Structured response simulating Gemini 1.5 Pro output.
        Uses persona-specific templates for realistic multi-agent debate.

        If GEMINI_API_KEY is configured (and google-generativeai is installed),
        routes non-classifier calls through the live Gemini REST API first.
        Falls back to deterministic templates on any error.
        """
        # Classifier is always local — deterministic keyword matching
        if persona == "classifier":
            return self._classifier_response(prompt)

        # Try live Gemini REST API if a key is configured
        try:
            from services.gemini_service import gemini_call, is_gemini_available
            if is_gemini_available():
                import json as _json
                context_str = _json.dumps(context or {}, default=str)
                full_prompt = (
                    f"[Persona: {persona or 'general'}]\n"
                    f"[Context: {context_str[:1000]}]\n\n"
                    f"{prompt}"
                )
                live_response = gemini_call(full_prompt)
                if live_response:
                    return live_response
        except Exception:
            pass  # Fall through to simulator templates

        if persona == "logistics_agent":
            return self._logistics_response(context or {})
        elif persona == "finance_agent":
            return self._finance_response(context or {})
        elif persona == "synthesis":
            return self._synthesis_response(context or {})
        elif persona == "email_generator":
            return self._email_response(context or {})
        else:
            return self._general_response(prompt)


    # ── Persona templates ────────────────────────────────────────────

    def _logistics_response(self, ctx):
        affected = ctx.get("affected_suppliers", [])
        signal = ctx.get("signal", "supply chain disruption")
        risk_appetite = ctx.get("risk_appetite", "balanced")

        primary_supplier = affected[0]["name"] if affected else "Primary Supplier"
        country = affected[0].get("country", "Unknown") if affected else "Unknown"

        speed_weight = {"conservative": 0.5, "balanced": 1.0, "aggressive": 2.0}.get(risk_appetite, 1.0)

        reroute_options = [
            {
                "option": "Air freight via alternative hub",
                "lead_time_shift_days": -5 * speed_weight,
                "feasibility": "high",
                "capacity_utilization": "72%",
            },
            {
                "option": f"Activate backup supplier in secondary region",
                "lead_time_shift_days": -3 * speed_weight,
                "feasibility": "medium",
                "capacity_utilization": "45%",
            },
            {
                "option": "Split shipment across multiple carriers",
                "lead_time_shift_days": -2 * speed_weight,
                "feasibility": "high",
                "capacity_utilization": "60%",
            },
        ]

        return {
            "agent": "Logistics Agent",
            "recommendation": f"Immediate rerouting recommended for {primary_supplier} ({country}) supply chain. "
                              f"Signal '{signal}' poses HIGH disruption risk to delivery timelines.",
            "lead_time_analysis": {
                "current_lead_time_days": 14,
                "disrupted_lead_time_days": 28,
                "lead_time_shift_days": 14,
                "sensitivity": "CRITICAL — 2-week delay cascades to 3 product lines",
            },
            "reroute_options": reroute_options,
            "service_level_impact": {
                "current_sla_compliance": "96.2%",
                "projected_sla_compliance": "78.5%",
                "at_risk_orders": 142,
            },
            "priority": "CRITICAL" if speed_weight >= 1.5 else "HIGH",
            "confidence": 78,
        }

    def _finance_response(self, ctx):
        affected = ctx.get("affected_suppliers", [])
        risk_appetite = ctx.get("risk_appetite", "balanced")

        cost_weight = {"conservative": 2.0, "balanced": 1.0, "aggressive": 0.5}.get(risk_appetite, 1.0)
        base_revenue = random.randint(800000, 2500000)

        sla_penalties = []
        for sup in affected[:3]:
            name = sup.get("name", "Supplier")
            penalty = round(random.randint(15000, 85000) * cost_weight)
            sla_penalties.append({
                "supplier": name,
                "sla_penalty_per_day": penalty // 10,
                "estimated_delay_days": random.randint(5, 21),
                "total_penalty": penalty,
            })

        expedited_cost = round(base_revenue * 0.12 * cost_weight)

        return {
            "agent": "Finance Agent",
            "recommendation": f"Cost-optimized mitigation path identified. Revenue-at-Risk: ${base_revenue:,}. "
                              f"Expedited shipping adds ${expedited_cost:,} but saves ${base_revenue - expedited_cost:,} in preserved revenue.",
            "sla_penalty_analysis": sla_penalties,
            "cost_breakdown": {
                "expedited_shipping_cost": expedited_cost,
                "standard_reroute_cost": round(expedited_cost * 0.4),
                "inventory_holding_cost": round(base_revenue * 0.03),
                "total_mitigation_cost": round(expedited_cost * 1.1),
            },
            "revenue_at_risk": base_revenue,
            "margin_impact": f"-{round(random.uniform(1.2, 4.8), 1)}%",
            "contract_penalties": {
                "triggered_clauses": random.randint(1, 4),
                "max_exposure": round(base_revenue * 0.15),
            },
            "priority": "HIGH" if cost_weight >= 1.5 else "MEDIUM",
            "confidence": 82,
        }

    def _synthesis_response(self, ctx):
        logistics = ctx.get("logistics_analysis", {})
        finance = ctx.get("finance_analysis", {})
        risk_appetite = ctx.get("risk_appetite", "balanced")
        lessons = ctx.get("past_lessons", [])
        erp_status = ctx.get("erp_inventory_status", [])

        revenue_at_risk = finance.get("revenue_at_risk", 1500000)
        logistics_conf = logistics.get("confidence", 75)
        finance_conf = finance.get("confidence", 80)
        combined_confidence = round((logistics_conf + finance_conf) / 2)

        # Past lessons influence
        lesson_modifier = ""
        if lessons:
            lesson_modifier = f" Historical data from {len(lessons)} similar event(s) incorporated — "
            if any(l.get("rating", 3) <= 2 for l in lessons):
                lesson_modifier += "past cost overruns flagged, adjusting estimates +15%."
                combined_confidence = max(combined_confidence - 8, 35)
            else:
                lesson_modifier += "prior strategies rated positively, high confidence in playbook."
                combined_confidence = min(combined_confidence + 5, 95)

        strategy_name = {
            "conservative": "Controlled Cost-First Mitigation",
            "balanced": "Balanced Speed-Cost Mitigation",
            "aggressive": "Rapid Response Maximum Coverage",
        }.get(risk_appetite, "Balanced Mitigation")

        return {
            "strategy_name": strategy_name,
            "confidence_score": combined_confidence,
            "summary": f"{strategy_name}: Multi-vector response targeting ${revenue_at_risk:,} revenue exposure."
                       f"{lesson_modifier} Recommended actions span logistics rerouting, financial hedging, "
                       f"and proactive supplier engagement.",
            "revenue_at_risk": revenue_at_risk,
            "mitigation_actions": self._build_dynamic_actions(erp_status),
            "executive_escalation_required": revenue_at_risk > ctx.get("revenue_threshold", 500000),
        }

    def _build_dynamic_actions(self, erp_status):
        actions = [
            {
                "id": f"act-email-{random.randint(100, 999)}",
                "type": "supplier_email",
                "title": "Supplier Contingency Notification",
                "description": "Auto-generated email to affected suppliers requesting contingency plan activation.",
                "priority": "HIGH",
                "timeline": "Immediate",
            }
        ]

        critical_components = [c for c in erp_status if c.get("status") == "CRITICAL"]
        if critical_components:
            names = ", ".join([c["name"] for c in critical_components[:2]])
            actions.append({
                "id": f"act-erp-{random.randint(100, 999)}",
                "type": "erp_adjustment",
                "title": f"Safety Stock Increase — {names}",
                "description": f"Increase safety stock levels by 30% for {len(critical_components)} critical component(s) currently below threshold.",
                "priority": "HIGH",
                "timeline": "24 hours",
                "target_skus": [c["component_id"] for c in critical_components]
            })

            actions.append({
                "id": f"act-po-{random.randint(100, 999)}",
                "type": "po_draft_update",
                "title": f"Pre-emptive PO Draft — {names}",
                "description": f"Draft purchase orders for 6-week buffer on critical components to secure capacity.",
                "priority": "MEDIUM",
                "timeline": "48 hours",
                "target_skus": [c["component_id"] for c in critical_components]
            })
        else:
            actions.extend([
                {
                    "id": f"act-erp-{random.randint(100, 999)}",
                    "type": "erp_adjustment",
                    "title": "Safety Stock Increase — All Components",
                    "description": "Increase safety stock levels by 15% across affected product lines to buffer delays.",
                    "priority": "HIGH",
                    "timeline": "24 hours",
                },
                {
                    "id": f"act-po-{random.randint(100, 999)}",
                    "type": "po_draft_update",
                    "title": "Pre-emptive Stock Build — Secondary Sources",
                    "description": "Initiate purchase orders from backup suppliers to build 4-week buffer stock.",
                    "priority": "MEDIUM",
                    "timeline": "48 hours",
                }
            ])
            
        return actions

    def _classifier_response(self, text):
        from modules.classifier import classifier
        return classifier.classify(text)


    def _email_response(self, ctx):
        supplier_name = ctx.get("supplier_name", "Valued Partner")
        company_name = ctx.get("company_name", "NexGen Electronics")
        disruption = ctx.get("disruption", "supply chain disruption")

        return {
            "subject": f"URGENT: Supply Chain Contingency Activation — {disruption[:50]}",
            "body": (
                f"Dear {supplier_name} Team,\n\n"
                f"We are writing to inform you of a developing situation that may impact our supply chain "
                f"partnership. Our AI-powered monitoring system has detected the following signal:\n\n"
                f'"{disruption}"\n\n'
                f"Based on our analysis, this event may affect delivery timelines and component availability. "
                f"As part of our Business Continuity Protocol, we are requesting the following:\n\n"
                f"1. Confirmation of current inventory levels for our active orders\n"
                f"2. Updated lead time estimates for the next 30-day window\n"
                f"3. Activation of any pre-agreed contingency supply routes\n"
                f"4. Status report on your own supply chain resilience measures\n\n"
                f"Please respond within 24 hours with the above information. Our Supply Chain team "
                f"is standing by to coordinate any necessary adjustments.\n\n"
                f"Best regards,\n"
                f"Supply Chain Operations\n"
                f"{company_name}"
            ),
        }

    def _general_response(self, prompt):
        return {
            "response": f"Analysis complete for: {prompt[:100]}",
            "confidence": 75,
        }


# ── Singleton export — toggle between real and simulated ─────────
from config import USE_REAL_VERTEX

if USE_REAL_VERTEX:
    try:
        from services.vertex_service import VertexAIService
        vertex_ai = VertexAIService()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"⚠️  Failed to init real Vertex AI: {e} — falling back to simulator")
        vertex_ai = VertexAISimulator()
else:
    vertex_ai = VertexAISimulator()
