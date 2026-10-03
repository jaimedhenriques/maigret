"""Authenticated partner notifications; deliveries never become attestations."""

import base64
import binascii
import os
import re

from flask import Blueprint, current_app, jsonify, request

from .store import audit, get_db, now_iso
from .vendor.standardwebhooks import Webhook, WebhookVerificationError

blueprint = Blueprint("workflow_ingress", __name__)


def init_workflow_ingress(app):
    app.config.setdefault("WORKFLOW_WEBHOOK_SECRET", os.getenv("VETRA_WORKFLOW_WEBHOOK_SECRET", ""))
    with app.app_context():
        db = get_db()
        with db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS workflow_deliveries (
                    event_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    candidate_id TEXT NOT NULL,
                    check_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(check_id,tenant_id,candidate_id) REFERENCES checks(id,tenant_id,candidate_id)
                )
            """)
    app.register_blueprint(blueprint)


@blueprint.post("/api/webhooks/workflow")
def receive_workflow_event():
    secret = current_app.config.get("WORKFLOW_WEBHOOK_SECRET", "")
    try:
        decoded = base64.b64decode(secret.removeprefix("whsec_"), validate=True)
        if len(decoded) < 32:
            raise ValueError("Weak secret")
        verifier = Webhook(secret)
    except (ValueError, TypeError, AttributeError, binascii.Error):
        return jsonify(error="Partner workflow webhook is not configured."), 503
    event_id = request.headers.get("webhook-id", "")
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", event_id):
        return jsonify(error="Invalid partner delivery."), 400
    try:
        event = verifier.verify(request.get_data(cache=False), dict(request.headers))
    except (WebhookVerificationError, ValueError, UnicodeError, TypeError, binascii.Error):
        return jsonify(error="Invalid partner signature or event."), 400
    if not isinstance(event, dict) or event.get("type") not in ("check.updated", "check.completed"):
        return jsonify(error="Unsupported partner notification."), 400
    references = event.get("data")
    if not isinstance(references, dict) or any(
        not isinstance(references.get(key), str) or not references[key] or len(references[key]) > 200
        for key in ("tenant_id", "candidate_id", "check_id")
    ):
        return jsonify(error="Invalid partner references."), 400
    tenant, candidate, check = (references[key] for key in ("tenant_id", "candidate_id", "check_id"))
    db = get_db()
    with db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT c.consent,c.status,c.sample FROM candidates c JOIN checks k "
            "ON k.candidate_id=c.id AND k.tenant_id=c.tenant_id "
            "WHERE c.tenant_id=? AND c.id=? AND k.id=?", (tenant, candidate, check),
        ).fetchone()
        if not row:
            return jsonify(error="Partner references do not match a recorded check."), 400
        previous = db.execute(
            "SELECT tenant_id,candidate_id,check_id FROM workflow_deliveries WHERE event_id=?", (event_id,),
        ).fetchone()
        if previous:
            if tuple(previous) != (tenant, candidate, check):
                return jsonify(error="Delivery ID conflicts with an earlier event."), 409
            return jsonify(received=True, duplicate=True, attestation=False)
        db.execute("INSERT INTO workflow_deliveries VALUES (?,?,?,?,?)",
                   (event_id, tenant, candidate, check, now_iso()))
        if not row["consent"] or row["status"] == "withdrawn":
            return jsonify(received=True, ignored=True, attestation=False)
        audit(tenant, "workflow.delivery", "Authenticated partner notification received; no verification attestation",
              candidate, actor_type="provider")
    # A contracted, provider-specific result mapper is required to change any check.
    return jsonify(received=True, attestation=False, status="notification_only")
