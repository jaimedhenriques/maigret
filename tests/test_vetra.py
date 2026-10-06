"""Security and consent invariants for the standalone Vetra pilot."""

import csv
import hashlib
import io
import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from jinja2 import DictLoader
from werkzeug.security import generate_password_hash

from vetra import create_app
from vetra.store import audit, create_checks, get_db, now_iso


@pytest.fixture
def app(tmp_path):
    app = create_app({"TESTING": True, "DEMO": True, "DATABASE": str(tmp_path / "pilot.sqlite3"),
                      "SECRET_KEY": "test-secret-key-that-is-at-least-32-characters", "IDENTITY_PROVIDER": None})
    app.jinja_loader = DictLoader({"workspace.html": "{{ csrf_token }}", "portal.html": "{{ csrf_token }}", "landing.html": "Vetra"})
    return app


@pytest.fixture
def client(app):
    client = app.test_client()
    client.get("/")
    return client


def csrf(client):
    with client.session_transaction() as session:
        return {"X-CSRF-Token": session["csrf"]}


def post(client, path, data=None):
    return client.post(path, json=data or {}, headers=csrf(client))


def invite(client, **values):
    body = {"name": "Jamie Example", "email": "jamie@example.test", "role": "Engineer", "package": "Professional"}
    body.update(values)
    response = post(client, "/api/candidates", body)
    assert response.status_code == 201, response.json
    data = response.json
    return data["candidate"]["id"], data["invitation_url"].rsplit("/", 1)[-1]


def check_id(client, cid, kind="identity"):
    return next(c["id"] for c in client.get(f"/api/candidates/{cid}").json["checks"] if c["kind"] == kind)


def portal_client(app, token):
    client = app.test_client()
    assert client.get(f"/api/portal/{token}").status_code == 200
    return client


def staff_as(app, client, role, tenant_id="demo"):
    with app.app_context():
        db = get_db()
        with db:
            row = db.execute("SELECT id FROM users WHERE tenant_id=? AND role=?", (tenant_id, role)).fetchone()
            if not row:
                user = db.execute(
                    "INSERT INTO users (tenant_id,name,email,password_hash,role,created_at) VALUES (?,?,?,?,?,?)",
                    (tenant_id, f"Test {role}", f"{role}-{tenant_id}@example.test",
                     generate_password_hash("a-long-test-password"), role, now_iso()),
                ).lastrowid
            else:
                user = row[0]
    with client.session_transaction() as session:
        session["user_id"] = user
        session["csrf"] = "staff-session-csrf-token"


def test_demo_is_explicit_and_never_provider_verified(client):
    overview = client.get("/api/overview").json
    assert overview["demo"] is True
    assert overview["metrics"]["total"] == 8
    assert overview["user"]["role"] == "owner"
    for candidate in client.get("/api/candidates").json["candidates"]:
        assert candidate["sample"] is True
        checks = client.get(f"/api/candidates/{candidate['id']}").json["checks"]
        assert all(c["status"] != "verified" for c in checks)


def test_staff_can_see_session_presence_without_provider_session_credentials(app, client):
    cid, _ = invite(client)
    identity_id = check_id(client, cid)
    checks = client.get(f"/api/candidates/{cid}").json["checks"]
    assert all(check["has_provider_session"] is False for check in checks)
    with app.app_context():
        db = get_db()
        with db:
            db.execute("UPDATE checks SET provider_session_id=? WHERE id=?", ("vs_private_fixture", identity_id))
    response = client.get(f"/api/candidates/{cid}")
    identity = next(check for check in response.json["checks"] if check["id"] == identity_id)
    assert identity["has_provider_session"] is True
    assert "provider_session_id" not in identity
    assert b"vs_private_fixture" not in response.data


def test_csrf_required_on_staff_and_candidate_mutations(app, client):
    assert client.post("/api/candidates", json={}).status_code == 403
    assert client.post("/api/logout", json={}, headers={"X-CSRF-Token": "wrong"}).status_code == 403
    cid, token = invite(client)
    portal = portal_client(app, token)
    assert portal.post(f"/api/portal/{token}/consent", json={"approved": True}).status_code == 403
    assert portal.post(f"/api/portal/{token}/withdraw", json={}).status_code == 403
    assert client.get(f"/api/candidates/{cid}").json["candidate"]["consent"] is False


def test_portal_does_not_create_staff_session(app, client):
    _cid, token = invite(client)
    portal = portal_client(app, token)
    assert portal.get("/api/candidates").status_code == 401
    data = portal.get(f"/api/portal/{token}").json
    assert set(data["candidate"]) == {"name", "role", "organization"}
    assert all("notes" not in check and "id" not in check for check in data["checks"])


def test_new_invitation_is_hashed_expiring_and_persistent(app, client):
    cid, token = invite(client)
    with app.app_context():
        stored = get_db().execute("SELECT * FROM invitations WHERE candidate_id=?", (cid,)).fetchone()
        assert stored["token_hash"] == hashlib.sha256(token.encode()).hexdigest()
        assert token not in dict(stored).values()
        expires = datetime.fromisoformat(stored["expires_at"])
        assert timedelta(days=6) < expires - datetime.now(timezone.utc) <= timedelta(days=7)
    portal = portal_client(app, token)
    assert portal.get(f"/api/portal/{token}").json["consent"] is False
    assert client.get(f"/api/candidates/{cid}").json["candidate"]["status"] == "invited"
    assert client.get("/api/audit").json["entries"][0]["action"] == "candidate.invited"


def test_reissue_revokes_previous_and_expired_tokens(app, client):
    cid, token = invite(client)
    response = post(client, f"/api/candidates/{cid}/invite")
    new_token = response.json["invitation_url"].rsplit("/", 1)[-1]
    assert new_token != token
    assert client.get(f"/api/portal/{token}").status_code == 404
    assert client.get(f"/api/portal/{new_token}").status_code == 200
    with app.app_context(), get_db() as db:
        db.execute("UPDATE invitations SET expires_at='2000-01-01T00:00:00+00:00' WHERE candidate_id=?", (cid,))
    assert client.get(f"/api/portal/{new_token}").status_code == 404


def test_consent_gates_reviews_provider_calls_and_claims(app, client):
    cid, token = invite(client)
    iid = check_id(client, cid)
    assert post(client, f"/api/candidates/{cid}/checks/{iid}/review", {"source": "Evidence", "notes": "Reviewed"}).status_code == 400
    assert post(client, f"/api/candidates/{cid}/checks/{iid}/start", {"provider": "stripe_identity"}).status_code == 400
    portal = portal_client(app, token)
    assert post(portal, f"/api/portal/{token}/submit", {"employment": "Candidate statement"}).status_code == 400
    assert post(portal, f"/api/portal/{token}/consent", {"approved": "true"}).status_code == 400
    response = post(portal, f"/api/portal/{token}/consent", {"approved": True})
    assert response.status_code == 200
    data = client.get(f"/api/candidates/{cid}").json
    assert data["candidate"]["consent"] is True
    assert all(c["status"] == "pending" for c in data["checks"])
    assert post(client, f"/api/candidates/{cid}/checks/{iid}/start", {"provider": "stripe_identity"}).status_code == 503


def test_candidate_claims_and_manual_reviews_do_not_verify(app, client):
    cid, token = invite(client)
    portal = portal_client(app, token)
    post(portal, f"/api/portal/{token}/consent", {"approved": True})
    response = post(portal, f"/api/portal/{token}/submit", {"employment": "Example employer 2022–2025", "education": "Example degree"})
    assert response.status_code == 200
    details = client.get(f"/api/candidates/{cid}").json
    assert details["candidate"]["status"] == "needs_review"
    assert next(c for c in details["checks"] if c["kind"] == "employment")["status"] == "needs_review"
    for check in details["checks"]:
        assert post(client, f"/api/candidates/{cid}/checks/{check['id']}/review", {"source": "Employer reference", "notes": "Reference was reviewed by staff."}).status_code == 200
    details = client.get(f"/api/candidates/{cid}").json
    assert details["candidate"]["status"] == "completed"
    assert all(check["status"] == "reviewed" for check in details["checks"])
    assert all(check["reviewed_by"] and check["reviewed_at"] for check in details["checks"])


def test_withdrawal_revokes_access_redacts_records_blocks_checks_and_exports(app, client):
    cid, token = invite(client)
    iid = check_id(client, cid)
    portal = portal_client(app, token)
    post(portal, f"/api/portal/{token}/consent", {"approved": True})
    post(portal, f"/api/portal/{token}/submit", {"employment": "Sensitive candidate statement"})
    post(portal, f"/api/portal/{token}/correction", {"message": "Sensitive correction"})
    assert post(portal, f"/api/portal/{token}/withdraw").status_code == 200
    assert portal.get(f"/api/portal/{token}").status_code == 404
    assert post(portal, f"/api/portal/{token}/consent", {"approved": True}).status_code == 404
    details = client.get(f"/api/candidates/{cid}").json
    assert details["candidate"]["status"] == "withdrawn"
    assert details["candidate"]["email"] == ""
    assert details["candidate"]["name"] == "Withdrawn candidate"
    assert details["checks"] == details["corrections"] == []
    assert post(client, f"/api/candidates/{cid}/checks/{iid}/review", {"source": "Evidence", "notes": "Review"}).status_code == 400
    assert post(client, f"/api/candidates/{cid}/invite").status_code == 409
    assert cid not in client.get("/api/export.csv").get_data(as_text=True)
    with app.app_context():
        db = get_db()
        assert not db.execute("SELECT 1 FROM claims WHERE candidate_id=?", (cid,)).fetchone()
        assert all(row[0] == "" for row in db.execute("SELECT notes FROM checks WHERE candidate_id=?", (cid,)))
        assert db.execute("SELECT message FROM corrections WHERE candidate_id=?", (cid,)).fetchone()[0] == ""


def test_correction_is_reviewable_and_reopens_case(app, client):
    cid, token = invite(client)
    portal = portal_client(app, token)
    post(portal, f"/api/portal/{token}/consent", {"approved": True})
    response = post(portal, f"/api/portal/{token}/correction", {"message": "My employment end date is 2025."})
    assert response.status_code == 201
    correction_id = response.json["correction_id"]
    details = client.get(f"/api/candidates/{cid}").json
    assert details["candidate"]["status"] == "needs_review"
    assert details["corrections"][0]["status"] == "open"
    assert post(client, f"/api/candidates/{cid}/corrections/{correction_id}/resolve", {"notes": "Updated according to reference."}).status_code == 200
    details = client.get(f"/api/candidates/{cid}").json
    assert details["corrections"][0]["status"] == "resolved"
    assert details["candidate"]["status"] == "in_progress"


def test_portal_retrieves_only_its_own_submissions_and_correction_outcomes(app, client):
    cid, token = invite(client)
    other_cid, other_token = invite(client, name="Other candidate", email="other@example.test")
    portal = portal_client(app, token)
    initial = portal.get(f"/api/portal/{token}").json
    assert initial["statements"] == {} and initial["corrections"] == []
    post(portal, f"/api/portal/{token}/consent", {"approved": True})
    post(portal, f"/api/portal/{token}/submit", {"employment": "My own employment statement", "education": "My own degree"})
    correction_id = post(portal, f"/api/portal/{token}/correction", {"message": "Correct my end date."}).json["correction_id"]
    post(client, f"/api/candidates/{cid}/corrections/{correction_id}/resolve", {"notes": "Your end date was corrected."})
    employment_id = check_id(client, cid, "employment")
    post(client, f"/api/candidates/{cid}/checks/{employment_id}/review", {"source": "Private employer contact", "notes": "Private HR review notes"})
    own = portal.get(f"/api/portal/{token}").json
    assert own["statements"] == {"employment": "My own employment statement", "education": "My own degree"}
    assert own["corrections"][0]["message"] == "Correct my end date."
    assert own["corrections"][0]["status"] == "resolved"
    assert own["corrections"][0]["resolution_notes"] == "Your end date was corrected."
    assert set(own["corrections"][0]) == {"message", "status", "resolution_notes", "created_at"}
    assert "Private HR review notes" not in json.dumps(own)
    assert "Private employer contact" not in json.dumps(own)
    other_portal = portal_client(app, other_token)
    post(other_portal, f"/api/portal/{other_token}/consent", {"approved": True})
    other = other_portal.get(f"/api/portal/{other_token}").json
    assert other["statements"] == {} and other["corrections"] == []
    assert other_cid != cid
    post(portal, f"/api/portal/{token}/withdraw")
    assert portal.get(f"/api/portal/{token}").status_code == 404


def test_tenant_isolation_applies_to_candidates_checks_audit_exports_and_users(app, client):
    cid, token = invite(client, name="Private tenant A candidate")
    iid = check_id(client, cid)
    with app.app_context(), get_db() as db:
        db.execute("INSERT INTO tenants VALUES ('other','Other tenant',?)", (now_iso(),))
        audit("other", "test.other", "Other tenant activity", actor_type="system")
    staff_as(app, client, "owner", "other")
    assert client.get("/api/candidates").json["candidates"] == []
    assert client.get(f"/api/candidates/{cid}").status_code == 404
    assert post(client, f"/api/candidates/{cid}/invite").status_code == 404
    assert post(client, f"/api/candidates/{cid}/checks/{iid}/review", {"notes": "n", "source": "s"}).status_code == 404
    assert client.get("/api/overview").json["metrics"]["total"] == 0
    assert all(entry["action"] == "test.other" for entry in client.get("/api/audit").json["entries"])
    assert "Private tenant A" not in client.get("/api/export.csv").get_data(as_text=True)
    assert all("-other@" in user["email"] for user in client.get("/api/users").json["users"])
    # A bearer invitation grants only that candidate's portal, irrespective of a staff session.
    assert client.get(f"/api/portal/{token}").json["candidate"]["name"] == "Private tenant A candidate"


def test_viewer_cannot_mutate_or_export_reviewer_cannot_create_users(app, client):
    cid, _token = invite(client)
    iid = check_id(client, cid)
    staff_as(app, client, "viewer")
    assert client.get(f"/api/candidates/{cid}").status_code == 200
    assert client.get("/api/export.csv").status_code == 403
    for path, body in [
        ("/api/candidates", {}), (f"/api/candidates/{cid}/invite", {}),
        (f"/api/candidates/{cid}/checks/{iid}/review", {"notes": "n", "source": "s"}),
        (f"/api/candidates/{cid}/checks/{iid}/start", {"provider": "stripe_identity"}),
        ("/api/users", {}),
    ]:
        assert post(client, path, body).status_code == 403
    staff_as(app, client, "reviewer")
    assert client.get("/api/users").status_code == 403
    assert post(client, "/api/users", {}).status_code == 403
    assert post(client, "/api/candidates", {"name": "New", "email": "new@example.test", "role": "Role", "package": "Essential"}).status_code == 201


def test_export_minimizes_and_neutralizes_spreadsheet_formulas(app, client):
    cid, token = invite(client, name="=HYPERLINK(\"evil\")", role="+SUM(1,1)")
    unconsented, _token2 = invite(client, name="Do not export")
    portal = portal_client(app, token)
    post(portal, f"/api/portal/{token}/consent", {"approved": True})
    response = client.get("/api/export.csv")
    rows = list(csv.DictReader(io.StringIO(response.get_data(as_text=True))))
    exported = next(row for row in rows if row["case_id"] == cid)
    assert exported["name"].startswith("'=")
    assert exported["job_role"].startswith("'+")
    assert "notes" not in exported and "source" not in exported
    assert all(row["case_id"] != unconsented for row in rows)


def test_audit_append_only_and_tokens_not_logged(app, client):
    _cid, token = invite(client)
    entries = client.get("/api/audit").json["entries"]
    assert token not in json.dumps(entries)
    with app.app_context():
        db = get_db()
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE audit SET message='rewritten' WHERE id=?", (entries[0]["id"],))
        db.rollback()
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("DELETE FROM audit WHERE id=?", (entries[0]["id"],))


def test_session_security_headers(client):
    response = client.get("/api/candidates")
    assert response.headers["Cache-Control"].startswith("no-store")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert "object-src 'none'" in response.headers["Content-Security-Policy"]


def test_non_demo_fails_closed_and_authenticates_bootstrap_owner(tmp_path):
    with pytest.raises(RuntimeError, match="stable"):
        create_app({"DEMO": False, "SECRET_KEY": None, "DATABASE": str(tmp_path / "closed.db")})
    with pytest.raises(RuntimeError, match="ADMIN"):
        create_app({"DEMO": False, "SECRET_KEY": "s" * 32, "DATABASE": str(tmp_path / "closed.db")})
    app = create_app({"TESTING": True, "DEMO": False, "SECRET_KEY": "s" * 32,
                      "DATABASE": str(tmp_path / "real.db"), "ADMIN_EMAIL": "owner@example.test",
                      "ADMIN_PASSWORD": "strong-initial-password", "SESSION_COOKIE_SECURE": False})
    app.jinja_loader = DictLoader({"workspace.html": "{{ user.name }}"})
    client = app.test_client()
    assert client.get("/").status_code == 302
    assert client.get("/api/candidates").status_code == 401
    client.get("/login")
    assert post(client, "/api/login", {"email": "owner@example.test", "password": "incorrect"}).status_code == 401
    old_csrf = csrf(client)
    assert post(client, "/api/login", {"email": "owner@example.test", "password": "strong-initial-password"}).status_code == 200
    assert csrf(client) != old_csrf
    assert client.get("/api/overview").json["metrics"]["total"] == 0
    with app.app_context():
        stored = get_db().execute("SELECT password_hash FROM users").fetchone()[0]
        assert stored != "strong-initial-password"
    assert post(client, "/api/logout").status_code == 200
    assert client.get("/api/candidates").status_code == 401


def test_non_demo_cannot_reuse_seeded_demo_database(app):
    with pytest.raises(RuntimeError, match="separate database"):
        create_app({"DEMO": False, "SECRET_KEY": "s" * 32, "DATABASE": app.config["DATABASE"],
                    "ADMIN_EMAIL": "owner@example.test", "ADMIN_PASSWORD": "strong-initial-password"})


def test_non_demo_refuses_example_placeholder_secrets(tmp_path):
    with pytest.raises(RuntimeError, match="stable"):
        create_app({"DEMO": False, "SECRET_KEY": "replace-with-a-random-stable-secret-of-at-least-32-characters",
                    "DATABASE": str(tmp_path / "placeholder.db"), "ADMIN_EMAIL": "owner@example.test",
                    "ADMIN_PASSWORD": "strong-initial-password"})
    with pytest.raises(RuntimeError, match="ADMIN"):
        create_app({"DEMO": False, "SECRET_KEY": "s" * 32, "DATABASE": str(tmp_path / "placeholder.db"),
                    "ADMIN_EMAIL": "owner@example.test", "ADMIN_PASSWORD": "replace-with-a-unique-password"})


def test_failed_login_attempts_are_throttled_without_storing_passwords(app, client):
    credentials = {"email": "unknown@example.test", "password": "do-not-store-this"}
    for _attempt in range(5):
        assert post(client, "/api/login", credentials).status_code == 401
    assert post(client, "/api/login", credentials).status_code == 429
    with app.app_context():
        row = get_db().execute("SELECT * FROM login_attempts").fetchone()
        assert row["failures"] == 5
        assert credentials["email"] not in dict(row).values()
        assert credentials["password"] not in dict(row).values()


def test_invalid_payloads_do_not_silently_store_data(client):
    assert post(client, "/api/candidates", {"name": "A", "email": "bad", "role": "B"}).status_code == 400
    assert post(client, "/api/candidates", {"name": "A", "email": "a@example.test", "role": "B", "package": "enterprise"}).status_code == 400
    assert post(client, "/api/candidates", {"name": 12, "email": "a@example.test", "role": "B"}).status_code == 400
    assert client.post("/api/candidates", json=["wrong"], headers=csrf(client)).status_code == 400


class FakeProvider:
    is_configured = True
    is_live = True

    def create_verification_session(self, **kwargs):
        self.metadata = {key: kwargs[key] for key in ("tenant_id", "candidate_id", "check_id")}
        return {"id": "vs_example", "url": "https://verify.stripe.com/example", "status": "requires_input", "livemode": True}

    def verify_webhook(self, raw_body, signature_header):
        if signature_header != "signed-test-event":
            raise ValueError("Invalid signature")
        return json.loads(raw_body)

    def cancel_verification_session(self, session_id):
        self.cancelled = session_id
        return {"id": session_id, "status": "canceled"}


def provider_event(provider, eid="evt_verified", status="verified", metadata=None):
    return {"id": eid, "livemode": True, "type": f"identity.verification_session.{status}", "data": {"object": {
        "id": "vs_example", "object": "identity.verification_session", "status": status,
        "metadata": metadata or provider.metadata,
    }}}


def webhook(client, event, signature="signed-test-event"):
    return client.post("/api/webhooks/stripe", data=json.dumps(event), content_type="application/json",
                       headers={"Stripe-Signature": signature})


def setup_provider(app, client):
    provider = FakeProvider()
    app.config.update(IDENTITY_PROVIDER=provider, PUBLIC_URL="https://pilot.example.test")
    cid, token = invite(client)
    portal = portal_client(app, token)
    post(portal, f"/api/portal/{token}/consent", {"approved": True})
    iid = check_id(client, cid)
    response = post(client, f"/api/candidates/{cid}/checks/{iid}/start", {"provider": "stripe_identity"})
    assert response.status_code == 200, response.json
    assert response.json["status"] == "in_progress"
    return provider, cid, token, iid


def test_provider_requires_valid_signature_matching_tenant_and_session(app, client):
    provider, cid, _token, iid = setup_provider(app, client)
    event = provider_event(provider)
    assert webhook(client, event, "forged").status_code == 400
    assert webhook(client, provider_event(provider, metadata={**provider.metadata, "tenant_id": "other"})).status_code == 400
    details = client.get(f"/api/candidates/{cid}").json
    assert next(c for c in details["checks"] if c["id"] == iid)["status"] == "in_progress"
    assert webhook(client, event).status_code == 200
    details = client.get(f"/api/candidates/{cid}").json
    assert next(c for c in details["checks"] if c["id"] == iid)["status"] == "verified"
    assert webhook(client, event).json["duplicate"] is True
    assert webhook(client, provider_event(provider, "evt_processing", "processing")).json["ignored"] is True
    details = client.get(f"/api/candidates/{cid}").json
    assert next(c for c in details["checks"] if c["id"] == iid)["status"] == "verified"


def test_provider_result_cannot_reintroduce_withdrawn_candidate_data(app, client):
    provider, cid, token, _iid = setup_provider(app, client)
    portal = portal_client(app, token)
    assert post(portal, f"/api/portal/{token}/withdraw").json["provider_cleanup"] == "requested"
    assert provider.cancelled == "vs_example"
    assert webhook(client, provider_event(provider)).json["ignored"] is True
    details = client.get(f"/api/candidates/{cid}").json
    assert details["candidate"]["status"] == "withdrawn"
    assert details["checks"] == []
    with app.app_context():
        assert get_db().execute("SELECT status FROM checks WHERE id=?", (_iid,)).fetchone()[0] != "verified"


def test_provider_cannot_process_fictional_seed_or_start_twice(app, client):
    provider, cid, _token, iid = setup_provider(app, client)
    assert post(client, f"/api/candidates/{cid}/checks/{iid}/start", {"provider": "stripe_identity"}).status_code == 409
    demo_iid = check_id(client, "demo-1")
    assert post(client, f"/api/candidates/demo-1/checks/{demo_iid}/start", {"provider": "stripe_identity"}).status_code == 409


def test_provider_requires_https_public_origin(app, client):
    app.config.update(IDENTITY_PROVIDER=FakeProvider(), PUBLIC_URL="http://public.example.test")
    cid, token = invite(client)
    portal = portal_client(app, token)
    post(portal, f"/api/portal/{token}/consent", {"approved": True})
    iid = check_id(client, cid)
    assert post(client, f"/api/candidates/{cid}/checks/{iid}/start", {"provider": "stripe_identity"}).status_code == 503


def test_test_mode_provider_events_never_attest_identity(app, client):
    provider, cid, _token, iid = setup_provider(app, client)
    event = provider_event(provider)
    event["livemode"] = False
    assert webhook(client, event).json["ignored"] is True
    check = next(c for c in client.get(f"/api/candidates/{cid}").json["checks"] if c["id"] == iid)
    assert check["status"] == "in_progress"
    provider.is_live = False
    assert client.get("/api/settings").json["capabilities"]["identity_provider"] is False


def test_consent_withdrawal_during_provider_request_stops_new_external_session(app, client):
    provider = FakeProvider()
    app.config.update(IDENTITY_PROVIDER=provider, PUBLIC_URL="https://pilot.example.test")
    cid, token = invite(client)
    portal = portal_client(app, token)
    post(portal, f"/api/portal/{token}/consent", {"approved": True})
    iid = check_id(client, cid)
    original = provider.create_verification_session

    def concurrent_withdrawal(**kwargs):
        result = original(**kwargs)
        # A separate connection models another request while the provider network call is in flight.
        with sqlite3.connect(app.config["DATABASE"]) as db:
            db.execute("UPDATE candidates SET consent=0,status='withdrawn' WHERE id=?", (cid,))
        return result

    provider.create_verification_session = concurrent_withdrawal
    response = post(client, f"/api/candidates/{cid}/checks/{iid}/start", {"provider": "stripe_identity"})
    assert response.status_code == 409
    assert provider.cancelled == "vs_example"
    with app.app_context():
        assert not get_db().execute("SELECT 1 FROM provider_sessions WHERE candidate_id=?", (cid,)).fetchone()
