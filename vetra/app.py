"""Consent-based HR workflow. This is a local pilot, not a screening provider."""

from __future__ import annotations

import csv
import hashlib
import hmac
import io
import os
import re
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from urllib.parse import urlsplit

from flask import (
    Flask, Response, abort, g, jsonify, redirect, render_template,
    render_template_string, request, session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from .store import audit, close_db, create_checks, get_db, init_db, now_iso, recompute_status


def _env_bool(key: str, default=True) -> bool:
    return os.environ.get(key, str(default)).strip().lower() in ("true", "1", "yes")


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        DEMO=_env_bool("VETRA_DEMO"),
        DATABASE=os.environ.get("VETRA_DATABASE", str(Path.cwd() / "instance" / "vetra.sqlite3")),
        SECRET_KEY=os.environ.get("VETRA_SECRET_KEY"),
        ADMIN_EMAIL=os.environ.get("VETRA_ADMIN_EMAIL", ""),
        ADMIN_PASSWORD=os.environ.get("VETRA_ADMIN_PASSWORD", ""),
        ADMIN_NAME=os.environ.get("VETRA_ADMIN_NAME", "Workspace owner"),
        ORGANIZATION=os.environ.get("VETRA_ORGANIZATION", "My organization"),
        PUBLIC_URL=os.environ.get("VETRA_PUBLIC_URL", ""),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=32768,
        JSON_SORT_KEYS=False,
    )
    if config:
        app.config.update(config)
    if app.config["DEMO"]:
        if not app.config["SECRET_KEY"]:
            app.config["SECRET_KEY"] = secrets.token_hex(32)
    else:
        secret = app.config["SECRET_KEY"]
        if not isinstance(secret, str) or len(secret) < 32 or secret.lower().startswith("replace-"):
            raise RuntimeError("Non-demo mode requires a stable VETRA_SECRET_KEY of at least 32 characters.")
        if (not _valid_email(app.config["ADMIN_EMAIL"]) or len(app.config["ADMIN_PASSWORD"]) < 12
                or app.config["ADMIN_PASSWORD"].lower().startswith("replace-")):
            raise RuntimeError("Non-demo mode requires VETRA_ADMIN_EMAIL and VETRA_ADMIN_PASSWORD (12+ characters).")
        if app.config["DATABASE"] == ":memory:":
            raise RuntimeError("Non-demo mode requires persistent SQLite storage.")
        app.config["SESSION_COOKIE_SECURE"] = (config or {}).get("SESSION_COOKIE_SECURE", True)
    app.teardown_appcontext(close_db)
    init_db(app)

    @app.before_request
    def protect_request():
        g.csp_nonce = secrets.token_urlsafe(20)
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(32)
        g.user = None
        if "user_id" in session:
            row = get_db().execute(
                "SELECT u.*,t.name AS organization FROM users u JOIN tenants t ON t.id=u.tenant_id "
                "WHERE u.id=?", (session["user_id"],)
            ).fetchone()
            if row:
                g.user = dict(row)
            else:
                session.clear()
                session["csrf"] = secrets.token_urlsafe(32)
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.endpoint not in (
            "stripe_webhook", "workflow_ingress.receive_workflow_event"
        ):
            token = request.headers.get("X-CSRF-Token", request.form.get("csrf_token", ""))
            expected = session.get("csrf", "")
            if not isinstance(token, str) or not expected or not hmac.compare_digest(token, expected):
                return jsonify(error="Your session expired. Refresh the page and try again."), 403

    @app.after_request
    def security_headers(response):
        nonce = getattr(g, "csp_nonce", "")
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; "
            "connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.path.startswith("/api/") or request.path.startswith("/candidate/") or request.path in ("/", "/app", "/login"):
            response.headers["Cache-Control"] = "no-store, private"
        if not app.config["DEMO"] and request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(405)
    @app.errorhandler(413)
    def http_error(error):
        if request.path.startswith("/api/"):
            return jsonify(error=error.description), error.code
        return error

    @app.errorhandler(500)
    def internal_error(_error):
        if request.path.startswith("/api/"):
            return jsonify(error="The request could not be completed. Try again later."), 500
        return "The request could not be completed. Try again later.", 500

    @app.get("/healthz")
    def healthz():
        get_db().execute("SELECT 1").fetchone()
        return jsonify(status="ok")

    @app.get("/")
    @app.get("/app")
    def workspace():
        if not g.user and app.config["DEMO"]:
            user_id = get_db().execute(
                "SELECT id FROM users WHERE tenant_id='demo' AND role='owner' ORDER BY id LIMIT 1"
            ).fetchone()[0]
            session["user_id"] = user_id
            session.permanent = True
            row = get_db().execute(
                "SELECT u.*,t.name AS organization FROM users u JOIN tenants t ON t.id=u.tenant_id WHERE u.id=?",
                (user_id,),
            ).fetchone()
            g.user = dict(row)
        if not g.user:
            return redirect(url_for("login_page"))
        return render_template("workspace.html", csrf_token=session["csrf"], demo=app.config["DEMO"],
                               user=_user_json(), csp_nonce=g.csp_nonce)

    @app.get("/about")
    def landing():
        return render_template("landing.html", demo=app.config["DEMO"], csp_nonce=g.csp_nonce)

    @app.get("/login")
    def login_page():
        return render_template_string(_LOGIN_PAGE, csrf_token=session["csrf"],
                                      demo=app.config["DEMO"], error=request.args.get("error", ""))

    @app.post("/login")
    @app.post("/api/login")
    def login():
        body = request.get_json(silent=True) if request.is_json else request.form
        if not isinstance(body, (dict, type(request.form))):
            return jsonify(error="Enter your email and password."), 400
        email = str(body.get("email", "")).strip().lower()
        password = str(body.get("password", ""))
        db = get_db()
        subject_hash = hashlib.sha256((email + "|" + (request.remote_addr or "unknown")).encode()).hexdigest()
        window_start = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat(timespec="seconds")
        attempt = db.execute("SELECT * FROM login_attempts WHERE subject_hash=?", (subject_hash,)).fetchone()
        if attempt and attempt["window_started_at"] > window_start and attempt["failures"] >= 5:
            return jsonify(error="Too many sign-in attempts. Try again in 15 minutes."), 429
        row = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        # Always run a password hash check, including unknown accounts.
        valid = check_password_hash(row["password_hash"] if row else _DUMMY_PASSWORD_HASH, password)
        if not row or not valid:
            with db:
                db.execute(
                    "INSERT INTO login_attempts VALUES (?,1,?) ON CONFLICT(subject_hash) DO UPDATE SET "
                    "failures=CASE WHEN window_started_at<? THEN 1 ELSE failures+1 END,"
                    "window_started_at=CASE WHEN window_started_at<? THEN excluded.window_started_at ELSE window_started_at END",
                    (subject_hash, now_iso(), window_start, window_start),
                )
                # Minimize abuse metadata: expired counters do not need indefinite storage.
                db.execute("DELETE FROM login_attempts WHERE window_started_at<?", (window_start,))
            if request.path == "/login":
                return render_template_string(_LOGIN_PAGE, csrf_token=session["csrf"],
                                              demo=app.config["DEMO"], error="Email or password is incorrect."), 401
            return jsonify(error="Email or password is incorrect."), 401
        session.clear()
        session["csrf"] = secrets.token_urlsafe(32)
        session["user_id"] = row["id"]
        session.permanent = True
        with db:
            db.execute("DELETE FROM login_attempts WHERE subject_hash=?", (subject_hash,))
            audit(row["tenant_id"], "session.login", "Staff member signed in", actor_id=row["id"])
        if request.path == "/login":
            return redirect(url_for("workspace"))
        return jsonify(ok=True, csrf_token=session["csrf"])

    @app.post("/api/logout")
    @require_staff()
    def logout():
        with get_db():
            audit(g.user["tenant_id"], "session.logout", "Staff member signed out", actor_id=g.user["id"])
        session.clear()
        return jsonify(ok=True)

    @app.get("/api/overview")
    @require_staff()
    def overview():
        rows = get_db().execute(
            "SELECT status,COUNT(*) AS count FROM candidates WHERE tenant_id=? GROUP BY status",
            (g.user["tenant_id"],),
        ).fetchall()
        counts = {r["status"]: r["count"] for r in rows}
        return jsonify(
            metrics={"total": sum(counts.values()), "in_progress": counts.get("in_progress", 0),
                     "needs_review": counts.get("needs_review", 0), "completed": counts.get("completed", 0)},
            activity=_activity(g.user["tenant_id"], limit=8), user=_user_json(), demo=app.config["DEMO"],
        )

    @app.get("/api/candidates")
    @require_staff()
    def list_candidates():
        search = request.args.get("search", "").strip()[:200]
        status = request.args.get("status", "").strip()
        params = [g.user["tenant_id"]]
        where = "c.tenant_id=?"
        if search:
            # LIKE wildcards from user input are literals, preserving predictable search results.
            escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            where += " AND (c.name LIKE ? ESCAPE '\\' OR c.email LIKE ? ESCAPE '\\' OR c.role LIKE ? ESCAPE '\\')"
            params.extend([f"%{escaped}%"] * 3)
        if status and status != "all":
            if status not in _STATUSES:
                return jsonify(error="Choose a valid candidate status."), 400
            where += " AND c.status=?"
            params.append(status)
        rows = get_db().execute(_CANDIDATE_SELECT + " WHERE " + where + " ORDER BY c.created_at DESC,c.id", params).fetchall()
        return jsonify(candidates=[_candidate_json(r) for r in rows])

    @app.get("/api/candidates/<candidate_id>")
    @require_staff()
    def candidate_detail(candidate_id):
        candidate = _get_candidate(candidate_id)
        checks = [] if candidate["status"] == "withdrawn" else [dict(r) for r in get_db().execute(
            "SELECT id,kind,label,status,source,notes,provider,sample,reviewed_at,reviewed_by "
            "FROM checks WHERE tenant_id=? AND candidate_id=? ORDER BY rowid",
            (g.user["tenant_id"], candidate_id),
        ).fetchall()]
        for check in checks:
            check["sample"] = bool(check["sample"])
        corrections = [] if candidate["status"] == "withdrawn" else [dict(r) for r in get_db().execute(
            "SELECT id,message,status,resolution_notes,created_at,resolved_at FROM corrections "
            "WHERE tenant_id=? AND candidate_id=? ORDER BY id DESC", (g.user["tenant_id"], candidate_id)
        ).fetchall()]
        return jsonify(candidate=_candidate_json(candidate), checks=checks, corrections=corrections,
                       activity=_activity(g.user["tenant_id"], candidate_id))

    @app.post("/api/candidates")
    @require_staff("owner", "reviewer")
    def new_candidate():
        body = _json_body()
        name, email, role = (_field(body, "name", 120), _field(body, "email", 254).lower(), _field(body, "role", 160))
        package = body.get("package", "Essential")
        if not name or not role or not _valid_email(email):
            return jsonify(error="Enter the candidate's name, a valid email, and the role."), 400
        if package not in ("Essential", "Professional"):
            return jsonify(error="Choose Essential or Professional."), 400
        candidate_id = uuid.uuid4().hex
        timestamp = now_iso()
        db = get_db()
        with db:
            db.execute(
                "INSERT INTO candidates (id,tenant_id,name,email,role,package,status,created_at,updated_at) "
                "VALUES (?,?,?,?,?,?,'invited',?,?)",
                (candidate_id, g.user["tenant_id"], name, email, role, package, timestamp, timestamp),
            )
            create_checks(db, g.user["tenant_id"], candidate_id, package)
            token = _create_invitation(g.user["tenant_id"], candidate_id)
            audit(g.user["tenant_id"], "candidate.invited", "Candidate invitation created; delivery is manual",
                  candidate_id, g.user["id"])
        return jsonify(candidate=_candidate_json(_get_candidate(candidate_id)),
                       invitation_url=url_for("candidate_portal", token=token), delivery="manual"), 201

    @app.post("/api/candidates/<candidate_id>/invite")
    @require_staff("owner", "reviewer")
    def reissue_invitation(candidate_id):
        candidate = _get_candidate(candidate_id)
        if candidate["status"] == "withdrawn":
            return jsonify(error="A withdrawn candidate cannot receive a new invitation."), 409
        with get_db():
            _lock_live_candidate(g.user["tenant_id"], candidate_id, consent_required=False)
            token = _create_invitation(g.user["tenant_id"], candidate_id)
            audit(g.user["tenant_id"], "invitation.reissued", "Fresh invitation created; previous invitation revoked",
                  candidate_id, g.user["id"])
        return jsonify(invitation_url=url_for("candidate_portal", token=token), delivery="manual")

    @app.post("/api/candidates/<candidate_id>/checks/<check_id>/review")
    @require_staff("owner", "reviewer")
    def review_check(candidate_id, check_id):
        candidate = _get_candidate(candidate_id)
        _ensure_consent(candidate)
        check = _get_check(candidate_id, check_id)
        body = _json_body()
        source, notes = _field(body, "source", 500), _field(body, "notes", 4000)
        if not source or not notes:
            return jsonify(error="Record the evidence source and your review notes."), 400
        if check["status"] == "verified":
            return jsonify(error="A provider verification cannot be replaced by a manual review."), 409
        with get_db():
            _lock_live_candidate(g.user["tenant_id"], candidate_id)
            check = _get_check(candidate_id, check_id)
            if check["status"] == "verified":
                return jsonify(error="A provider verification cannot be replaced by a manual review."), 409
            get_db().execute(
                "UPDATE checks SET status='reviewed',source=?,notes=?,provider='Manual review',"
                "reviewed_by=?,reviewed_at=? WHERE tenant_id=? AND candidate_id=? AND id=?",
                (source, notes, g.user["id"], now_iso(), g.user["tenant_id"], candidate_id, check_id),
            )
            recompute_status(get_db(), g.user["tenant_id"], candidate_id)
            audit(g.user["tenant_id"], "check.reviewed", f"{check['label']} manually reviewed; no provider attestation",
                  candidate_id, g.user["id"])
        return jsonify(ok=True, status="reviewed", candidate=_candidate_json(_get_candidate(candidate_id)))

    @app.post("/api/candidates/<candidate_id>/corrections/<int:correction_id>/resolve")
    @require_staff("owner", "reviewer")
    def resolve_correction(candidate_id, correction_id):
        candidate = _get_candidate(candidate_id)
        _ensure_consent(candidate)
        notes = _field(_json_body(), "notes", 4000)
        if not notes:
            return jsonify(error="Record how the correction was handled."), 400
        with get_db():
            _lock_live_candidate(g.user["tenant_id"], candidate_id)
            result = get_db().execute(
                "UPDATE corrections SET status='resolved',resolution_notes=?,resolved_by=?,resolved_at=? "
                "WHERE tenant_id=? AND candidate_id=? AND id=? AND status='open'",
                (notes, g.user["id"], now_iso(), g.user["tenant_id"], candidate_id, correction_id),
            )
            if not result.rowcount:
                abort(404, description="Open correction not found.")
            recompute_status(get_db(), g.user["tenant_id"], candidate_id)
            audit(g.user["tenant_id"], "correction.resolved", "Candidate correction resolved by a reviewer",
                  candidate_id, g.user["id"])
        return jsonify(ok=True, candidate=_candidate_json(_get_candidate(candidate_id)))

    @app.post("/api/candidates/<candidate_id>/checks/<check_id>/start")
    @require_staff("owner", "reviewer")
    def start_provider_check(candidate_id, check_id):
        candidate = _get_candidate(candidate_id)
        _ensure_consent(candidate)
        check = _get_check(candidate_id, check_id)
        body = _json_body()
        if body.get("provider") != "stripe_identity" or check["kind"] != "identity":
            return jsonify(error="Only Stripe Identity is supported for identity checks."), 400
        provider = _provider()
        public_url = app.config["PUBLIC_URL"].rstrip("/")
        if not provider or not provider.is_configured or not _valid_public_url(public_url):
            return jsonify(error="Identity provider is not configured. Configure Stripe Identity and an HTTPS public URL."), 503
        if not getattr(provider, "is_live", False):
            return jsonify(error="A live Stripe Identity account is required. Test mode cannot attest a person's identity."), 503
        if candidate["sample"]:
            return jsonify(error="Fictional demo candidates cannot be submitted to a real identity provider."), 409
        if check["provider_session_id"] or check["status"] == "verified":
            return jsonify(error="An identity verification session already exists for this check."), 409
        # Provider return URL contains no invitation bearer token.
        return_url = public_url + url_for("verification_return")
        try:
            result = provider.create_verification_session(
                tenant_id=g.user["tenant_id"], candidate_id=candidate_id, check_id=check_id,
                return_url=return_url, idempotency_key=f"vetra-{check_id}",
            )
        except Exception:
            app.logger.warning("Identity provider session creation failed")
            return jsonify(error="The identity provider could not start the session. Try again later."), 502
        if (not isinstance(result, dict) or not result.get("id") or not _valid_https_url(result.get("url", ""))
                or result.get("livemode") is not True):
            return jsonify(error="The identity provider returned an invalid session."), 502
        db = get_db()
        # Re-read under a write lock: consent can change during the external request.
        try:
            db.execute("BEGIN IMMEDIATE")
            fresh = db.execute("SELECT consent,status FROM candidates WHERE tenant_id=? AND id=?",
                               (g.user["tenant_id"], candidate_id)).fetchone()
            if not fresh["consent"] or fresh["status"] == "withdrawn":
                db.rollback()
                cleanup = _cancel_or_redact(provider, result["id"])
                with db:
                    audit(g.user["tenant_id"], "provider.withdrawal", "In-flight identity session stopped after withdrawal"
                          if cleanup else "In-flight identity session cleanup needs staff follow-up",
                          candidate_id, actor_type="system")
                return jsonify(error="Consent was withdrawn before the session could be recorded."), 409
            db.execute(
                "INSERT INTO provider_sessions (session_id,tenant_id,candidate_id,check_id,verification_url,created_at) VALUES (?,?,?,?,?,?)",
                (result["id"], g.user["tenant_id"], candidate_id, check_id, result["url"], now_iso()),
            )
            changed = db.execute(
                "UPDATE checks SET status='in_progress',provider='Stripe Identity',provider_session_id=? "
                "WHERE tenant_id=? AND candidate_id=? AND id=? AND provider_session_id IS NULL",
                (result["id"], g.user["tenant_id"], candidate_id, check_id),
            )
            if not changed.rowcount:
                db.rollback()
                return jsonify(error="An identity session is already being processed."), 409
            recompute_status(db, g.user["tenant_id"], candidate_id)
            audit(g.user["tenant_id"], "provider.started", "Stripe Identity session started; no result yet",
                  candidate_id, g.user["id"])
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            return jsonify(error="An identity session is already being processed."), 409
        return jsonify(status="in_progress", verification_url=result["url"], provider="stripe_identity")

    @app.get("/verification/return")
    def verification_return():
        return render_template_string(
            "<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
            "<title>Vetra · verification submitted</title><body><main><h1>Thank you</h1>"
            "<p>Your identity session has been submitted. Your employer will receive the provider's result "
            "when it is available. You can return to the invitation to view your case or request a correction.</p>"
            "</main></body></html>"
        )

    @app.post("/api/webhooks/stripe")
    def stripe_webhook():
        provider = _provider()
        if not provider:
            return jsonify(error="Identity provider is not configured."), 503
        try:
            event = provider.verify_webhook(request.get_data(cache=False), request.headers.get("Stripe-Signature", ""))
        except Exception:
            return jsonify(error="Invalid webhook signature or event."), 400
        if not isinstance(event, dict) or not isinstance(event.get("id"), str):
            return jsonify(error="Invalid provider event."), 400
        if event.get("livemode") is not True or not getattr(provider, "is_live", False):
            return jsonify(received=True, ignored=True, reason="Test mode events cannot attest identity.")
        event_type = event.get("type")
        supported = {"identity.verification_session.verified", "identity.verification_session.requires_input",
                     "identity.verification_session.processing", "identity.verification_session.canceled"}
        if not isinstance(event_type, str) or event_type not in supported:
            return jsonify(received=True, ignored=True)
        data = event.get("data", {})
        obj = data.get("object", {}) if isinstance(data, dict) else {}
        if (not isinstance(obj, dict) or obj.get("object") != "identity.verification_session"
                or not isinstance(obj.get("id"), str)):
            return jsonify(error="Invalid verification session."), 400
        db = get_db()
        with db:
            db.execute("BEGIN IMMEDIATE")
            provider_session = db.execute("SELECT * FROM provider_sessions WHERE session_id=?", (obj.get("id"),)).fetchone()
            if not provider_session:
                return jsonify(received=True, ignored=True)
            metadata = obj.get("metadata", {})
            if not isinstance(metadata, dict) or any(str(metadata.get(k)) != str(provider_session[k])
                                                    for k in ("tenant_id", "candidate_id", "check_id")):
                return jsonify(error="Verification metadata does not match the recorded session."), 400
            if db.execute("SELECT 1 FROM provider_events WHERE event_id=?", (event["id"],)).fetchone():
                return jsonify(received=True, duplicate=True)
            tenant_id, candidate_id, check_id = (provider_session[k] for k in ("tenant_id", "candidate_id", "check_id"))
            candidate = db.execute("SELECT * FROM candidates WHERE tenant_id=? AND id=?", (tenant_id, candidate_id)).fetchone()
            check = db.execute("SELECT * FROM checks WHERE tenant_id=? AND candidate_id=? AND id=?",
                               (tenant_id, candidate_id, check_id)).fetchone()
            if not candidate["consent"] or candidate["status"] == "withdrawn" or candidate["sample"]:
                db.execute("INSERT INTO provider_events VALUES (?,?,?)", (event["id"], obj["id"], now_iso()))
                audit(tenant_id, "provider.ignored", "Provider event discarded after consent withdrawal or for a sample",
                      candidate_id, actor_type="provider")
                return jsonify(received=True, ignored=True)
            # A late processing/retry event cannot downgrade a verified result.
            if check["status"] == "verified":
                db.execute("INSERT INTO provider_events VALUES (?,?,?)", (event["id"], obj["id"], now_iso()))
                return jsonify(received=True, ignored=True)
            expected_status = {
                "identity.verification_session.verified": "verified",
                "identity.verification_session.requires_input": "requires_input",
                "identity.verification_session.processing": "processing",
                "identity.verification_session.canceled": "canceled",
            }[event_type]
            if obj.get("status") != expected_status:
                return jsonify(error="Provider event and verification state disagree."), 400
            db.execute("INSERT INTO provider_events VALUES (?,?,?)", (event["id"], obj["id"], now_iso()))
            status = "verified" if expected_status == "verified" else (
                "in_progress" if expected_status == "processing" else "needs_review")
            db.execute(
                "UPDATE checks SET status=?,source='Signed Stripe Identity webhook',"
                "notes=?,provider='Stripe Identity',reviewed_at=? "
                "WHERE tenant_id=? AND candidate_id=? AND id=? AND provider_session_id=?",
                (status, "Provider attested identity verification." if status == "verified" else
                 "Identity provider session requires follow-up; no identity attestation.",
                 now_iso(), tenant_id, candidate_id, check_id, obj["id"]),
            )
            recompute_status(db, tenant_id, candidate_id)
            audit(tenant_id, "provider.result", f"Stripe Identity session state: {expected_status}",
                  candidate_id, actor_type="provider")
        return jsonify(received=True)

    @app.get("/api/audit")
    @require_staff()
    def audit_log():
        return jsonify(entries=_activity(g.user["tenant_id"], limit=200))

    @app.get("/api/export.csv")
    @require_staff("owner", "reviewer")
    def export():
        out = io.StringIO(newline="")
        writer = csv.writer(out)
        writer.writerow(["case_id", "name", "email", "job_role", "package", "workflow_status", "consent_at", "updated_at", "sample"])
        with get_db():
            get_db().execute("BEGIN IMMEDIATE")
            rows = get_db().execute(
                "SELECT id,name,email,role,package,status,consent_at,updated_at,sample FROM candidates "
                "WHERE tenant_id=? AND consent=1 AND status!='withdrawn' ORDER BY created_at DESC",
                (g.user["tenant_id"],),
            ).fetchall()
            for row in rows:
                writer.writerow([_safe_csv_cell(value) for value in row])
            audit(g.user["tenant_id"], "report.exported", "Consented workflow records exported",
                  actor_id=g.user["id"])
        return Response(out.getvalue(), mimetype="text/csv", headers={
            "Content-Disposition": 'attachment; filename="vetra-consented-cases.csv"',
        })

    @app.get("/api/settings")
    @require_staff()
    def settings():
        provider = _provider()
        identity_configured = bool(provider and provider.is_configured and getattr(provider, "is_live", False)
                                   and _valid_public_url(app.config["PUBLIC_URL"]))
        return jsonify(
            organization=g.user["organization"], demo=app.config["DEMO"], mode="local_pilot",
            capabilities={"consent": True, "manual_review": True, "audit_trail": True,
                          "tenant_isolation": True, "role_permissions": True, "candidate_corrections": True,
                          "identity_provider": identity_configured, "employment_provider": False,
                          "education_provider": False, "sanctions": False, "criminal_records": False,
                          "billing": False, "sso": False, "email_delivery": False},
            readiness={"identity": "Configured" if identity_configured else "Not configured",
                       "employment": "Manual evidence review", "education": "Manual evidence review",
                       "email": "Copy invitation link; no email is sent", "hosting": "Local pilot",
                       "screening": "No criminal, credit, or sanctions data sources connected",
                       "production": "Independent security, privacy, legal, and operational review required"},
            providers=[{"id": "stripe_identity", "name": "Stripe Identity", "configured": identity_configured,
                        "description": "Hosted identity session with signed verification webhooks."}],
            consent_policy_version="vetra-pilot-v1",
            limitations=["Manual reviews are not provider attestations.",
                         "Fictional samples never represent real identity or background verification.",
                         "No automated hiring decisions or social-account searches."],
        )

    @app.get("/api/users")
    @require_staff("owner")
    def list_users():
        rows = get_db().execute("SELECT id,name,email,role,created_at FROM users WHERE tenant_id=? ORDER BY id",
                                (g.user["tenant_id"],)).fetchall()
        return jsonify(users=[dict(r) for r in rows])

    @app.post("/api/users")
    @require_staff("owner")
    def new_user():
        body = _json_body()
        name, email = _field(body, "name", 120), _field(body, "email", 254).lower()
        password, role = body.get("password", ""), body.get("role", "reviewer")
        if not name or not _valid_email(email) or not isinstance(password, str) or len(password) < 12:
            return jsonify(error="Enter a name, valid email, and a password of at least 12 characters."), 400
        if role not in ("owner", "reviewer", "viewer"):
            return jsonify(error="Choose owner, reviewer, or viewer."), 400
        try:
            with get_db():
                result = get_db().execute(
                    "INSERT INTO users (tenant_id,name,email,password_hash,role,created_at) VALUES (?,?,?,?,?,?)",
                    (g.user["tenant_id"], name, email, generate_password_hash(password), role, now_iso()),
                )
                audit(g.user["tenant_id"], "user.created", f"Staff account created with {role} role", actor_id=g.user["id"])
        except sqlite3.IntegrityError:
            return jsonify(error="This email is already registered."), 409
        return jsonify(user={"id": result.lastrowid, "name": name, "email": email, "role": role}), 201

    @app.get("/candidate/<token>")
    def candidate_portal(token):
        _portal_candidate(token)
        return render_template("portal.html", token=token, csrf_token=session["csrf"], demo=app.config["DEMO"],
                               csp_nonce=g.csp_nonce)

    @app.get("/api/portal/<token>")
    def portal_data(token):
        candidate, invitation = _portal_candidate(token)
        organization = get_db().execute("SELECT name FROM tenants WHERE id=?", (candidate["tenant_id"],)).fetchone()[0]
        checks = [dict(r) for r in get_db().execute(
            "SELECT k.kind,k.label,k.status,p.verification_url FROM checks k LEFT JOIN provider_sessions p "
            "ON p.session_id=k.provider_session_id AND p.tenant_id=k.tenant_id AND p.candidate_id=k.candidate_id "
            "WHERE k.tenant_id=? AND k.candidate_id=? ORDER BY k.rowid",
            (candidate["tenant_id"], candidate["id"]),
        ).fetchall()]
        for check in checks:
            if not candidate["consent"] or check["status"] in ("verified", "reviewed") or not check["verification_url"]:
                check.pop("verification_url", None)
        statements = {}
        corrections = []
        if candidate["consent"]:
            statements = {row["kind"]: row["statement"] for row in get_db().execute(
                "SELECT kind,statement FROM claims WHERE tenant_id=? AND candidate_id=?",
                (candidate["tenant_id"], candidate["id"]),
            ).fetchall()}
            corrections = [dict(row) for row in get_db().execute(
                "SELECT message,status,resolution_notes,created_at FROM corrections "
                "WHERE tenant_id=? AND candidate_id=? ORDER BY id DESC",
                (candidate["tenant_id"], candidate["id"]),
            ).fetchall()]
        return jsonify(candidate={"name": candidate["name"], "role": candidate["role"], "organization": organization},
                       checks=checks, consent=bool(candidate["consent"]), status=candidate["status"],
                       expires_at=invitation["expires_at"], sample=bool(candidate["sample"]),
                       policy_version="vetra-pilot-v1", csrf_token=session["csrf"],
                       statements=statements, corrections=corrections)

    @app.post("/api/portal/<token>/consent")
    def portal_consent(token):
        candidate, _invitation = _portal_candidate(token)
        if _json_body().get("approved") is not True:
            return jsonify(error="Consent must be explicitly approved."), 400
        with get_db():
            candidate = _lock_live_candidate(candidate["tenant_id"], candidate["id"], consent_required=False)
            _portal_candidate(token)
            if not candidate["consent"]:
                timestamp = now_iso()
                get_db().execute(
                    "UPDATE candidates SET consent=1,consent_at=?,updated_at=? WHERE tenant_id=? AND id=? AND status!='withdrawn'",
                    (timestamp, timestamp, candidate["tenant_id"], candidate["id"]),
                )
                get_db().execute(
                    "INSERT INTO consent_events (tenant_id,candidate_id,approved,policy_version,created_at) VALUES (?,?,1,?,?)",
                    (candidate["tenant_id"], candidate["id"], "vetra-pilot-v1", timestamp),
                )
                recompute_status(get_db(), candidate["tenant_id"], candidate["id"])
                audit(candidate["tenant_id"], "consent.granted", "Candidate explicitly consented to the requested checks",
                      candidate["id"], actor_type="candidate")
        return jsonify(ok=True, consent=True, status="in_progress")

    @app.post("/api/portal/<token>/submit")
    def portal_submit(token):
        candidate, _invitation = _portal_candidate(token)
        _ensure_consent(candidate)
        body = _json_body()
        allowed = {r[0] for r in get_db().execute("SELECT kind FROM checks WHERE tenant_id=? AND candidate_id=?",
                                                (candidate["tenant_id"], candidate["id"]))}
        claims = {kind: _field(body, kind, 2500) for kind in ("employment", "education", "professional_profile")
                  if kind in allowed and kind in body}
        claims = {key: value for key, value in claims.items() if value}
        if not claims:
            return jsonify(error="Add at least one statement for the requested checks."), 400
        if "professional_profile" in claims and not _valid_https_url(claims["professional_profile"], allow_http=True):
            return jsonify(error="The professional profile must be a valid http or https URL."), 400
        with get_db():
            _lock_live_candidate(candidate["tenant_id"], candidate["id"])
            _portal_candidate(token)
            for kind, statement in claims.items():
                get_db().execute(
                    "INSERT INTO claims (tenant_id,candidate_id,kind,statement,created_at) VALUES (?,?,?,?,?) "
                    "ON CONFLICT(tenant_id,candidate_id,kind) DO UPDATE SET statement=excluded.statement,created_at=excluded.created_at",
                    (candidate["tenant_id"], candidate["id"], kind, statement, now_iso()),
                )
                get_db().execute(
                    "UPDATE checks SET status='needs_review',notes=?,source='Candidate-provided statement',"
                    "provider='',reviewed_by=NULL,reviewed_at=NULL WHERE tenant_id=? AND candidate_id=? AND kind=?",
                    (statement, candidate["tenant_id"], candidate["id"], kind),
                )
            recompute_status(get_db(), candidate["tenant_id"], candidate["id"])
            audit(candidate["tenant_id"], "candidate.submitted", "Candidate statements submitted for human review",
                  candidate["id"], actor_type="candidate")
        return jsonify(ok=True, status="needs_review")

    @app.post("/api/portal/<token>/correction")
    def portal_correction(token):
        candidate, _invitation = _portal_candidate(token)
        _ensure_consent(candidate)
        message = _field(_json_body(), "message", 4000)
        if not message:
            return jsonify(error="Describe the information you want corrected."), 400
        with get_db():
            _lock_live_candidate(candidate["tenant_id"], candidate["id"])
            _portal_candidate(token)
            result = get_db().execute(
                "INSERT INTO corrections (tenant_id,candidate_id,message,created_at) VALUES (?,?,?,?)",
                (candidate["tenant_id"], candidate["id"], message, now_iso()),
            )
            recompute_status(get_db(), candidate["tenant_id"], candidate["id"])
            audit(candidate["tenant_id"], "correction.requested", "Candidate requested an information correction",
                  candidate["id"], actor_type="candidate")
        return jsonify(ok=True, correction_id=result.lastrowid, status="needs_review"), 201

    @app.post("/api/portal/<token>/withdraw")
    def portal_withdraw(token):
        candidate, _invitation = _portal_candidate(token)
        timestamp = now_iso()
        db = get_db()
        provider_sessions = []
        with db:
            _lock_live_candidate(candidate["tenant_id"], candidate["id"], consent_required=False)
            _portal_candidate(token)
            db.execute(
                "UPDATE candidates SET status='withdrawn',consent=0,withdrawn_at=?,updated_at=?,"
                "name='Withdrawn candidate',email='',role='' WHERE tenant_id=? AND id=?",
                (timestamp, timestamp, candidate["tenant_id"], candidate["id"]),
            )
            db.execute("UPDATE invitations SET revoked_at=? WHERE tenant_id=? AND candidate_id=?",
                       (timestamp, candidate["tenant_id"], candidate["id"]))
            provider_sessions = [row[0] for row in db.execute(
                "SELECT session_id FROM provider_sessions WHERE tenant_id=? AND candidate_id=?",
                (candidate["tenant_id"], candidate["id"]),
            ).fetchall()]
            db.execute("UPDATE provider_sessions SET verification_url='' WHERE tenant_id=? AND candidate_id=?",
                       (candidate["tenant_id"], candidate["id"]))
            db.execute("UPDATE checks SET notes='',source='',reviewed_by=NULL,reviewed_at=NULL "
                       "WHERE tenant_id=? AND candidate_id=?", (candidate["tenant_id"], candidate["id"]))
            db.execute("DELETE FROM claims WHERE tenant_id=? AND candidate_id=?", (candidate["tenant_id"], candidate["id"]))
            db.execute("UPDATE corrections SET message='',resolution_notes='',status='withdrawn' "
                       "WHERE tenant_id=? AND candidate_id=?", (candidate["tenant_id"], candidate["id"]))
            db.execute(
                "INSERT INTO consent_events (tenant_id,candidate_id,approved,policy_version,created_at) VALUES (?,?,0,?,?)",
                (candidate["tenant_id"], candidate["id"], "vetra-pilot-v1", timestamp),
            )
            audit(candidate["tenant_id"], "consent.withdrawn", "Consent withdrawn; portal revoked and report details removed",
                  candidate["id"], actor_type="candidate")
        cleanup = "not_required"
        if provider_sessions:
            provider = _provider()
            cleanup = "requested"
            for provider_session in provider_sessions:
                if not _cancel_or_redact(provider, provider_session):
                    cleanup = "follow_up_required"
            with db:
                audit(candidate["tenant_id"], "provider.withdrawal", "Provider cancellation/redaction requested" if cleanup == "requested"
                      else "Provider cancellation/redaction needs staff follow-up", candidate["id"], actor_type="system")
        return jsonify(ok=True, status="withdrawn", provider_cleanup=cleanup,
                       message="Consent withdrawn. Your portal link is revoked and your report is unavailable.")

    from .workflow_ingress import init_workflow_ingress
    init_workflow_ingress(app)
    return app


_STATUSES = {"invited", "in_progress", "needs_review", "completed", "withdrawn"}
_DUMMY_PASSWORD_HASH = generate_password_hash("nonexistent-user-placeholder")
_CANDIDATE_SELECT = """
SELECT c.*,
(SELECT COUNT(*) FROM checks k WHERE k.tenant_id=c.tenant_id AND k.candidate_id=c.id) AS checks_total,
(SELECT COUNT(*) FROM checks k WHERE k.tenant_id=c.tenant_id AND k.candidate_id=c.id
 AND k.status IN ('reviewed','verified')) AS checks_completed
FROM candidates c
"""


def require_staff(*roles):
    def decorate(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not g.user:
                return jsonify(error="Sign in to access this workspace."), 401
            if roles and g.user["role"] not in roles:
                return jsonify(error="Your role does not allow this action."), 403
            return view(*args, **kwargs)
        return wrapped
    return decorate


def _user_json():
    return {k: g.user[k] for k in ("name", "email", "role", "organization")}


def _candidate_json(candidate):
    fields = ("id", "name", "email", "role", "package", "status", "created_at", "updated_at")
    result = {key: candidate[key] for key in fields}
    result.update(consent=bool(candidate["consent"]), sample=bool(candidate["sample"]),
                  checks_total=candidate["checks_total"], checks_completed=candidate["checks_completed"],
                  initials="".join(part[0] for part in candidate["name"].split()[:2]).upper())
    if candidate["status"] == "withdrawn":
        result["checks_total"] = result["checks_completed"] = 0
    return result


def _get_candidate(candidate_id):
    candidate = get_db().execute(_CANDIDATE_SELECT + " WHERE c.tenant_id=? AND c.id=?",
                                 (g.user["tenant_id"], candidate_id)).fetchone()
    if not candidate:
        abort(404, description="Candidate not found.")
    return candidate


def _get_check(candidate_id, check_id):
    check = get_db().execute("SELECT * FROM checks WHERE tenant_id=? AND candidate_id=? AND id=?",
                             (g.user["tenant_id"], candidate_id, check_id)).fetchone()
    if not check:
        abort(404, description="Check not found.")
    return check


def _activity(tenant_id, candidate_id=None, limit=50):
    where, params = "a.tenant_id=?", [tenant_id]
    if candidate_id:
        where += " AND a.candidate_id=?"
        params.append(candidate_id)
    params.append(limit)
    rows = get_db().execute(
        "SELECT a.id,a.action,a.message,a.created_at,a.candidate_id,a.actor_type,u.name AS actor "
        "FROM audit a LEFT JOIN users u ON u.id=a.actor_id WHERE " + where + " ORDER BY a.id DESC LIMIT ?", params
    ).fetchall()
    return [dict(row) for row in rows]


def _json_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        abort(400, description="Send a JSON object.")
    return body


def _field(body, key, maximum):
    value = body.get(key, "")
    if not isinstance(value, str) or len(value) > maximum:
        abort(400, description=f"{key.replace('_', ' ').capitalize()} must be text up to {maximum} characters.")
    value = value.strip()
    if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
        abort(400, description="Text contains unsupported control characters.")
    return value


def _valid_email(value):
    return isinstance(value, str) and len(value) <= 254 and bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value))


def _valid_https_url(value, allow_http=False):
    if not isinstance(value, str) or any(char.isspace() for char in value):
        return False
    try:
        parsed = urlsplit(value)
        return (parsed.scheme in (("https", "http") if allow_http else ("https",))
                and bool(parsed.hostname) and not parsed.username and not parsed.password)
    except ValueError:
        return False


def _valid_public_url(value):
    return _valid_https_url(value) and not urlsplit(value).query and not urlsplit(value).fragment


def _ensure_consent(candidate):
    if candidate["status"] == "withdrawn":
        abort(400, description="Consent has been withdrawn. No checks or reporting are available.")
    if not candidate["consent"]:
        abort(400, description="Candidate consent is required before any check or review.")


def _lock_live_candidate(tenant_id, candidate_id, consent_required=True):
    """Serialize consent changes with every operation that processes a candidate."""
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    candidate = db.execute("SELECT * FROM candidates WHERE tenant_id=? AND id=?", (tenant_id, candidate_id)).fetchone()
    if candidate is None or candidate["status"] == "withdrawn":
        abort(400, description="Consent has been withdrawn. No checks or reporting are available.")
    if consent_required:
        _ensure_consent(candidate)
    return candidate


def _create_invitation(tenant_id, candidate_id):
    token = secrets.token_urlsafe(32)
    timestamp = now_iso()
    expiry = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(timespec="seconds")
    get_db().execute("UPDATE invitations SET revoked_at=? WHERE tenant_id=? AND candidate_id=? AND revoked_at IS NULL",
                     (timestamp, tenant_id, candidate_id))
    get_db().execute("INSERT INTO invitations VALUES (?,?,?,?,NULL,?)",
                     (hashlib.sha256(token.encode()).hexdigest(), tenant_id, candidate_id, expiry, timestamp))
    return token


def _portal_candidate(token):
    if len(token) < 32 or len(token) > 128:
        abort(404, description="This invitation is unavailable or has expired.")
    invitation = get_db().execute(
        "SELECT * FROM invitations WHERE token_hash=? AND revoked_at IS NULL AND expires_at>?",
        (hashlib.sha256(token.encode()).hexdigest(), now_iso()),
    ).fetchone()
    if not invitation:
        abort(404, description="This invitation is unavailable or has expired.")
    candidate = get_db().execute(
        "SELECT * FROM candidates WHERE tenant_id=? AND id=? AND status!='withdrawn'",
        (invitation["tenant_id"], invitation["candidate_id"]),
    ).fetchone()
    if not candidate:
        abort(404, description="This invitation is unavailable or has expired.")
    return candidate, invitation


def _provider():
    # Injection makes protocol/consent tests independent of a network and API key.
    from flask import current_app

    if "IDENTITY_PROVIDER" in current_app.config:
        return current_app.config["IDENTITY_PROVIDER"]
    try:
        from .providers import StripeIdentityProvider
        return StripeIdentityProvider.from_env()
    except ImportError:
        return None


def _cancel_or_redact(provider, session_id):
    if not provider:
        return False
    try:
        provider.cancel_verification_session(session_id)
        return True
    except Exception:
        try:
            provider.redact_verification_session(session_id)
            return True
        except Exception:
            return False


def _safe_csv_cell(value):
    text = str(value) if value is not None else ""
    # Spreadsheet programs also ignore leading whitespace when deciding to run formulas.
    if text.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")):
        return "'" + text
    return text


_LOGIN_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sign in · Vetra</title><style>
body{margin:0;font:16px system-ui;color:#182a30;background:#f2f5f3;display:grid;place-items:center;min-height:100vh}
main{background:white;padding:40px;border-radius:20px;max-width:360px;width:80%;box-shadow:0 8px 40px #102a1010}
label{display:block;margin-top:20px}input,button{box-sizing:border-box;width:100%;padding:13px;border-radius:8px;border:1px solid #b6c4c0;margin-top:7px;font:inherit}
button{background:#153d32;color:white;margin-top:24px;cursor:pointer}a{color:#153d32}.error{color:#ad3228}
</style></head><body><main><h1>Welcome to Vetra</h1><p>Sign in to your verification workspace.</p>
{% if error %}<p class="error" role="alert">{{ error }}</p>{% endif %}
<form method="post" action="/login"><input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<label for="email">Work email</label><input type="email" id="email" name="email" autocomplete="username" required maxlength="254">
<label for="password">Password</label><input type="password" id="password" name="password" autocomplete="current-password" required>
<button type="submit">Sign in</button></form><p><a href="/about">About Vetra</a></p>
{% if demo %}<p><a href="/">Open fictional demo</a></p>{% endif %}</main></body></html>"""
