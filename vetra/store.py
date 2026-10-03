"""SQLite storage with explicit tenant keys and append-only application audit records."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app, g
from werkzeug.security import generate_password_hash


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS tenants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL REFERENCES tenants(id),
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('owner','reviewer','viewer')),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS login_attempts (
    subject_hash TEXT PRIMARY KEY,
    failures INTEGER NOT NULL,
    window_started_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS candidates (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id),
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    role TEXT NOT NULL,
    package TEXT NOT NULL CHECK(package IN ('Essential','Professional')),
    status TEXT NOT NULL CHECK(status IN ('invited','in_progress','needs_review','completed','withdrawn')),
    consent INTEGER NOT NULL DEFAULT 0,
    consent_at TEXT,
    withdrawn_at TEXT,
    sample INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(id, tenant_id)
);
CREATE TABLE IF NOT EXISTS checks (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('identity','employment','education','professional_profile')),
    label TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending','in_progress','needs_review','reviewed','verified')),
    source TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    provider TEXT NOT NULL DEFAULT '',
    provider_session_id TEXT,
    reviewed_by INTEGER REFERENCES users(id),
    reviewed_at TEXT,
    sample INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(candidate_id,tenant_id) REFERENCES candidates(id,tenant_id),
    UNIQUE(id,tenant_id,candidate_id)
);
CREATE TABLE IF NOT EXISTS invitations (
    token_hash TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(candidate_id,tenant_id) REFERENCES candidates(id,tenant_id)
);
CREATE TABLE IF NOT EXISTS consent_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    approved INTEGER NOT NULL,
    policy_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(candidate_id,tenant_id) REFERENCES candidates(id,tenant_id)
);
CREATE TABLE IF NOT EXISTS claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    statement TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(candidate_id,tenant_id) REFERENCES candidates(id,tenant_id),
    UNIQUE(tenant_id,candidate_id,kind)
);
CREATE TABLE IF NOT EXISTS corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','resolved','withdrawn')),
    resolution_notes TEXT NOT NULL DEFAULT '',
    resolved_by INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    FOREIGN KEY(candidate_id,tenant_id) REFERENCES candidates(id,tenant_id)
);
CREATE TABLE IF NOT EXISTS provider_sessions (
    session_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    check_id TEXT NOT NULL,
    verification_url TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY(check_id,tenant_id,candidate_id) REFERENCES checks(id,tenant_id,candidate_id)
);
CREATE TABLE IF NOT EXISTS provider_events (
    event_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES provider_sessions(session_id),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL REFERENCES tenants(id),
    actor_id INTEGER REFERENCES users(id),
    actor_type TEXT NOT NULL,
    candidate_id TEXT,
    action TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS candidates_tenant ON candidates(tenant_id,status);
CREATE INDEX IF NOT EXISTS checks_candidate ON checks(tenant_id,candidate_id);
CREATE INDEX IF NOT EXISTS audit_tenant ON audit(tenant_id,id);
CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit
BEGIN SELECT RAISE(ABORT, 'Audit records are append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit
BEGIN SELECT RAISE(ABORT, 'Audit records are append-only'); END;
"""


def get_db() -> sqlite3.Connection:
    if "vetra_db" not in g:
        db = sqlite3.connect(current_app.config["DATABASE"], timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("PRAGMA busy_timeout = 10000")
        g.vetra_db = db
    return g.vetra_db


def close_db(_error=None) -> None:
    db = g.pop("vetra_db", None)
    if db is not None:
        db.close()


def audit(tenant_id: str, action: str, message: str, candidate_id=None,
          actor_id=None, actor_type="staff") -> None:
    get_db().execute(
        "INSERT INTO audit (tenant_id,actor_id,actor_type,candidate_id,action,message,created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (tenant_id, actor_id, actor_type, candidate_id, action, message, now_iso()),
    )


CHECK_LABELS = {
    "identity": "Identity review",
    "employment": "Employment history",
    "education": "Education credentials",
    "professional_profile": "Professional profile",
}


def package_kinds(package: str) -> tuple[str, ...]:
    return ("identity", "employment") if package == "Essential" else tuple(CHECK_LABELS)


def create_checks(db: sqlite3.Connection, tenant_id: str, candidate_id: str,
                  package: str, sample=False) -> None:
    import uuid

    for kind in package_kinds(package):
        db.execute(
            "INSERT INTO checks (id,tenant_id,candidate_id,kind,label,status,sample) "
            "VALUES (?,?,?,?,?,'pending',?)",
            (uuid.uuid4().hex, tenant_id, candidate_id, kind, CHECK_LABELS[kind], int(sample)),
        )


def recompute_status(db: sqlite3.Connection, tenant_id: str, candidate_id: str) -> None:
    candidate = db.execute(
        "SELECT consent,status FROM candidates WHERE tenant_id=? AND id=?",
        (tenant_id, candidate_id),
    ).fetchone()
    if candidate is None or candidate["status"] == "withdrawn":
        return
    statuses = [r[0] for r in db.execute(
        "SELECT status FROM checks WHERE tenant_id=? AND candidate_id=?", (tenant_id, candidate_id)
    ).fetchall()]
    correction_open = db.execute(
        "SELECT 1 FROM corrections WHERE tenant_id=? AND candidate_id=? AND status='open' LIMIT 1",
        (tenant_id, candidate_id),
    ).fetchone()
    if not candidate["consent"]:
        status = "invited"
    elif correction_open or "needs_review" in statuses:
        status = "needs_review"
    elif statuses and all(s in ("reviewed", "verified") for s in statuses):
        status = "completed"
    else:
        status = "in_progress"
    db.execute("UPDATE candidates SET status=?,updated_at=? WHERE tenant_id=? AND id=?",
               (status, now_iso(), tenant_id, candidate_id))


def init_db(app) -> None:
    database = Path(app.config["DATABASE"])
    database.parent.mkdir(parents=True, exist_ok=True)
    with app.app_context():
        db = get_db()
        db.executescript(SCHEMA)
        if "verification_url" not in {row["name"] for row in db.execute("PRAGMA table_info(provider_sessions)")}:
            db.execute("ALTER TABLE provider_sessions ADD COLUMN verification_url TEXT NOT NULL DEFAULT ''")
        if app.config["DEMO"]:
            _seed_demo(db)
        else:
            _bootstrap_admin(db, app.config)
        db.commit()
    # Local pilot records should not be world-readable.
    if str(database) != ":memory:" and database.exists():
        database.chmod(0o600)


def _bootstrap_admin(db, config) -> None:
    if db.execute("SELECT 1 FROM tenants WHERE id='demo'").fetchone():
        raise RuntimeError("Non-demo mode requires a separate database without fictional demo records.")
    if db.execute("SELECT 1 FROM users LIMIT 1").fetchone():
        return
    import uuid

    tenant_id = uuid.uuid4().hex
    db.execute("INSERT INTO tenants VALUES (?,?,?)",
               (tenant_id, config["ORGANIZATION"], now_iso()))
    db.execute(
        "INSERT INTO users (tenant_id,name,email,password_hash,role,created_at) VALUES (?,?,?,?,?,?)",
        (tenant_id, config["ADMIN_NAME"], config["ADMIN_EMAIL"].lower(),
         generate_password_hash(config["ADMIN_PASSWORD"]), "owner", now_iso()),
    )
    audit(tenant_id, "workspace.created", "Workspace initialized", actor_type="system")


def _seed_demo(db) -> None:
    if db.execute("SELECT 1 FROM tenants WHERE id='demo'").fetchone():
        return
    import secrets

    timestamp = now_iso()
    db.execute("INSERT INTO tenants VALUES ('demo',?,?)", ("Northstar · fictional demo", timestamp))
    db.execute(
        "INSERT INTO users (tenant_id,name,email,password_hash,role,created_at) VALUES (?,?,?,?,?,?)",
        ("demo", "Alex Morgan", "alex@example.test", generate_password_hash(secrets.token_urlsafe(32)),
         "owner", timestamp),
    )
    actor = db.execute("SELECT id FROM users WHERE tenant_id='demo'").fetchone()[0]
    people = [
        ("Maya Chen", "Product designer", "Professional", "needs_review"),
        ("Oliver Reed", "Engineering manager", "Professional", "in_progress"),
        ("Amara Okafor", "Operations lead", "Essential", "completed"),
        ("Lucas Silva", "Software engineer", "Professional", "invited"),
        ("Sofia Patel", "People partner", "Essential", "completed"),
        ("Elias Laurent", "Account executive", "Essential", "needs_review"),
        ("Nora Williams", "Data analyst", "Professional", "in_progress"),
        ("Theo Brooks", "Finance manager", "Professional", "invited"),
    ]
    for index, (name, role, package, status) in enumerate(people, 1):
        cid = f"demo-{index}"
        consent = status != "invited"
        db.execute(
            "INSERT INTO candidates (id,tenant_id,name,email,role,package,status,consent,consent_at,"
            "sample,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (cid, "demo", name, f"candidate{index}@example.test", role, package, status,
             int(consent), timestamp if consent else None, 1, timestamp, timestamp),
        )
        create_checks(db, "demo", cid, package, sample=True)
        if consent:
            db.execute(
                "INSERT INTO consent_events (tenant_id,candidate_id,approved,policy_version,created_at) "
                "VALUES ('demo',?,1,'demo-example-v1',?)", (cid, timestamp)
            )
        if status == "completed":
            db.execute(
                "UPDATE checks SET status='reviewed',source='Fictional demonstration evidence',"
                "notes='Sample manual review. No real identity or employment verification performed.',"
                "provider='Demo manual review',reviewed_by=?,reviewed_at=? WHERE candidate_id=?",
                (actor, timestamp, cid),
            )
        elif status == "needs_review":
            db.execute(
                "UPDATE checks SET status='needs_review',source='Fictional candidate statement',"
                "notes='Illustrative candidate claim awaiting a human review.' "
                "WHERE candidate_id=? AND kind='employment'", (cid,)
            )
        elif status == "in_progress":
            db.execute(
                "UPDATE checks SET status='in_progress',notes='Illustrative workflow only.' "
                "WHERE candidate_id=? AND kind='employment'", (cid,)
            )
        audit("demo", "demo.seeded", "Fictional sample candidate added", cid,
              actor_type="system")
