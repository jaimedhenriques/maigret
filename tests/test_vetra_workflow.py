"""Tests for copied MIT verifier integration and non-attesting partner ingress."""

import base64
import json
from datetime import datetime, timedelta, timezone

import pytest

from vetra import create_app
from vetra.store import get_db
from vetra.vendor.standardwebhooks import Webhook

SECRET = "whsec_" + base64.b64encode(b"a" * 32).decode()


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True, "DEMO": True, "SECRET_KEY": "test",
                       "DATABASE": str(tmp_path / "workflow.sqlite"), "WORKFLOW_WEBHOOK_SECRET": SECRET})


def references(app):
    with app.app_context():
        row = get_db().execute(
            "SELECT c.tenant_id,c.id AS candidate_id,k.id AS check_id FROM candidates c JOIN checks k "
            "ON k.candidate_id=c.id AND k.tenant_id=c.tenant_id WHERE c.consent=1 LIMIT 1"
        ).fetchone()
        return dict(row)


def post(app, data=None, *, event_id="msg_test", age=0, mutate=False, headers=None):
    body = json.dumps({"type": "check.completed", "data": data or references(app)})
    timestamp = datetime.now(timezone.utc) - timedelta(seconds=age)
    signed = {"webhook-id": event_id, "webhook-timestamp": str(int(timestamp.timestamp())),
              "webhook-signature": Webhook(SECRET).sign(event_id, timestamp, body)}
    if mutate:
        body += " "
    if headers:
        signed.update(headers)
    return app.test_client().post("/api/webhooks/workflow", data=body, content_type="application/json",
                                  headers=signed)


def test_signed_delivery_is_audited_but_never_attests(app):
    ref = references(app)
    with app.app_context():
        before = get_db().execute("SELECT status FROM checks WHERE id=?", (ref["check_id"],)).fetchone()[0]
    result = post(app, ref)
    assert result.status_code == 200
    assert result.json["attestation"] is False
    with app.app_context():
        assert get_db().execute("SELECT status FROM checks WHERE id=?", (ref["check_id"],)).fetchone()[0] == before
        assert get_db().execute("SELECT COUNT(*) FROM audit WHERE action='workflow.delivery'").fetchone()[0] == 1


def test_duplicate_delivery_does_not_repeat_audit(app):
    assert post(app).status_code == 200
    assert post(app).json["duplicate"] is True
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM audit WHERE action='workflow.delivery'").fetchone()[0] == 1


@pytest.mark.parametrize("age", [301, -301])
def test_stale_or_future_delivery_rejected(app, age):
    assert post(app, age=age).status_code == 400


def test_tampered_body_rejected(app):
    assert post(app, mutate=True).status_code == 400


@pytest.mark.parametrize("signature", ["broken", "v1,!!!", "v2,abc", "v1,ZmFrZQ=="])
def test_malformed_signature_is_a_safe_error(app, signature):
    assert post(app, headers={"webhook-signature": signature}).status_code == 400


def test_cross_tenant_reference_rejected(app):
    ref = references(app)
    ref["tenant_id"] = "another-tenant"
    assert post(app, ref).status_code == 400


def test_no_consent_delivery_cannot_apply_result(app):
    ref = references(app)
    with app.app_context():
        db = get_db()
        with db:
            db.execute("UPDATE candidates SET consent=0 WHERE id=?", (ref["candidate_id"],))
    result = post(app, ref)
    assert result.json["ignored"] is True
    assert result.json["attestation"] is False


def test_unconfigured_receiver_fails_closed(app):
    app.config["WORKFLOW_WEBHOOK_SECRET"] = ""
    assert post(app).status_code == 503


def test_delivery_id_cannot_be_rebound_to_another_check(app):
    ref = references(app)
    assert post(app, ref).status_code == 200
    with app.app_context():
        other = get_db().execute("SELECT id FROM checks WHERE candidate_id=? AND id!=?",
                                (ref["candidate_id"], ref["check_id"])).fetchone()[0]
    ref["check_id"] = other
    assert post(app, ref).status_code == 409
