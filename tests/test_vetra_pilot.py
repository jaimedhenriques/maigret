"""Paid-pilot boundaries: recovery, authenticated billing, and recoverable snapshots."""
import hashlib
import json
import sqlite3
from datetime import datetime,timedelta,timezone

import pytest
from vetra import create_app
from vetra.store import get_db

@pytest.fixture
def app(tmp_path):
    return create_app({'TESTING':True,'DEMO':False,'DATABASE':str(tmp_path/'pilot.db'),'SECRET_KEY':'s'*40,'ADMIN_EMAIL':'owner@example.test','ADMIN_PASSWORD':'initial-password-123','PUBLIC_URL':'https://example.test','SESSION_COOKIE_SECURE':False})

def headers(client):
    with client.session_transaction() as s:return {'X-CSRF-Token':s['csrf']}

def login(client):
    client.get('/login');r=client.post('/api/login',json={'email':'owner@example.test','password':'initial-password-123'},headers=headers(client));assert r.status_code==200

def test_reset_single_use_expiry_and_session_revocation(app):
    old=app.test_client();login(old)
    token='secret-reset-token';digest=hashlib.sha256(token.encode()).hexdigest()
    with app.app_context():
        db=get_db();db.execute('INSERT INTO password_resets VALUES (?,1,?,NULL)',(digest,(datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat()));db.commit()
    reset=app.test_client();assert reset.get('/reset-password/'+token).status_code==200
    assert reset.post('/reset-password/'+token,data={'password':'changed-password-123','csrf_token':headers(reset)['X-CSRF-Token']}).status_code==200
    assert old.get('/api/overview').status_code==401
    assert reset.get('/reset-password/'+token).status_code==400
    with app.app_context():
        db=get_db();db.execute('INSERT INTO password_resets VALUES (?,1,?,NULL)',('expired',(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat()));db.commit()
    assert reset.get('/reset-password/no-such-token').status_code==400

def test_recovery_does_not_enumerate_and_is_throttled(app,monkeypatch):
    from vetra import pilot
    monkeypatch.setattr(pilot,'email_ready',lambda:True)
    messages=[];monkeypatch.setattr(pilot,'send_email',lambda *args:messages.append(args) or True)
    c=app.test_client();c.get('/forgot-password')
    a=c.post('/forgot-password',data={'email':'owner@example.test','csrf_token':headers(c)['X-CSRF-Token']})
    b=c.post('/forgot-password',data={'email':'nobody@example.test','csrf_token':headers(c)['X-CSRF-Token']})
    assert a.data==b.data
    c.post('/forgot-password',data={'email':'owner@example.test','csrf_token':headers(c)['X-CSRF-Token']})
    assert len(messages)==1
    assert '/reset-password/' in messages[0][2]

def test_unconfigured_billing_and_private_pages(app):
    c=app.test_client();c.get('/login')
    assert c.get('/pilot').status_code==302
    assert c.post('/api/billing/checkout',json={},headers=headers(c)).status_code==403
    login(c)
    assert c.post('/api/billing/checkout',json={},headers=headers(c)).status_code==503
    assert c.get('/pilot').status_code==200
    assert 'no-store' in c.get('/pilot').headers['Cache-Control']
    assert c.get('/privacy').status_code==200

def test_live_billing_cannot_charge_during_free_early_access(app,monkeypatch):
    """A configured live account cannot silently turn free access into checkout."""
    from vetra import pilot
    monkeypatch.setenv('STRIPE_SECRET_KEY','sk_live_fixture')
    monkeypatch.setenv('STRIPE_PILOT_PRICE_ID','price_fixture')
    monkeypatch.setenv('STRIPE_BILLING_WEBHOOK_SECRET','whsec_fixture')
    # Browser fields and query parameters cannot override the server setting.
    app.config['BILLING_ENABLED']=False
    def forbidden_network(*args,**kwargs):
        pytest.fail('Free early access must never contact Stripe checkout')
    monkeypatch.setattr(pilot,'build_opener',forbidden_network)
    c=app.test_client();login(c)
    response=c.post('/api/billing/checkout?billing_enabled=true',json={'billing_enabled':True},headers=headers(c))
    assert response.status_code==503
    assert 'no payment is required' in response.json['error']
    page=c.get('/pilot').data
    assert b'Free early access' in page
    assert b'id="pay"' not in page
    with app.app_context():
        assert pilot.billing_configured() is True
        assert pilot.billing_ready() is False
        assert get_db().execute('SELECT COUNT(*) FROM pilot_payments').fetchone()[0]==0

def test_billing_requires_explicit_server_enable(app,monkeypatch):
    from vetra import pilot
    monkeypatch.setenv('STRIPE_SECRET_KEY','sk_live_fixture')
    monkeypatch.setenv('STRIPE_PILOT_PRICE_ID','price_fixture')
    monkeypatch.setenv('STRIPE_BILLING_WEBHOOK_SECRET','whsec_fixture')
    with app.app_context():
        assert pilot.billing_ready() is False
        app.config['BILLING_ENABLED']='false'
        assert pilot.billing_ready() is False
        app.config['BILLING_ENABLED']=True
        assert pilot.billing_ready() is True

def test_billing_webhook_signed_bound_and_deduplicated(app,monkeypatch):
    import hmac,time
    monkeypatch.setenv('STRIPE_SECRET_KEY','sk_live_fixture')
    monkeypatch.setenv('STRIPE_PILOT_PRICE_ID','price_fixture')
    monkeypatch.setenv('STRIPE_BILLING_WEBHOOK_SECRET','whsec_fixture')
    # Existing signed payment receipts are reconciled even while new checkout is disabled.
    app.config['BILLING_ENABLED']=False
    with app.app_context():
        db=get_db();tid=db.execute('SELECT tenant_id FROM users').fetchone()[0];db.execute('INSERT INTO pilot_payments VALUES (?,?,?, ?,NULL)',('cs_live_fixture',tid,'pending','2026-01-01'));db.commit()
    def send(tenant):
        raw=json.dumps({'id':'evt_fixture','type':'checkout.session.completed','livemode':True,'data':{'object':{'id':'cs_live_fixture','client_reference_id':tenant,'metadata':{'tenant_id':tenant},'mode':'payment','livemode':True,'payment_status':'paid'}}}).encode();timestamp=str(int(time.time()));sig=hmac.new(b'whsec_fixture',timestamp.encode()+b'.'+raw,hashlib.sha256).hexdigest()
        return app.test_client().post('/api/webhooks/billing',data=raw,headers={'Stripe-Signature':f't={timestamp},v1={sig}'})
    assert send('other-tenant').status_code==400
    assert send(tid).status_code==200
    assert send(tid).status_code==200
    with app.app_context():
        assert get_db().execute('SELECT status FROM pilot_payments').fetchone()[0]=='paid'
        assert get_db().execute('SELECT COUNT(*) FROM billing_events').fetchone()[0]==1

def test_time_logs_cannot_cross_tenants(app):
    c=app.test_client();login(c)
    assert c.post('/api/pilot/time',json={'candidate_id':'foreign','minutes':10,'baseline_minutes':30},headers=headers(c)).status_code==404
    assert c.post('/api/pilot/time',json={'candidate_id':'foreign','minutes':True,'baseline_minutes':30},headers=headers(c)).status_code==400

def test_effort_measurement_keeps_negative_savings_and_updates_totals(app):
    c=app.test_client();login(c)
    with app.app_context():
        db=get_db();tid=db.execute('SELECT tenant_id FROM users').fetchone()[0]
        db.execute("INSERT INTO candidates(id,tenant_id,name,email,role,package,status,consent,consent_at,sample,created_at,updated_at) VALUES (?,?,?,?,?,'Essential','in_progress',1,?,0,?,?)",('real-case',tid,'Sample Person','person@example.test','Analyst','2026-10-01','2026-10-01','2026-10-01'))
        db.commit()
    page=c.get('/pilot').data
    assert b'value="real-case"' in page
    response=c.post('/api/pilot/time',json={'candidate_id':'real-case','minutes':30,'baseline_minutes':12},headers=headers(c))
    assert response.status_code==200
    assert response.json['saved_minutes']==-18
    assert response.json['measurements']==1
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM audit WHERE action='pilot.effort_recorded'").fetchone()[0]==1

def test_encrypted_backup_restore_and_wrong_key(app,tmp_path):
    crypto = pytest.importorskip("cryptography.fernet", reason="Backup tools use standalone Vetra dependencies")
    Fernet, InvalidToken = crypto.Fernet, crypto.InvalidToken
    from vetra.operations import backup,restore,retention_candidates
    key=Fernet.generate_key();archive=tmp_path/'sealed.backup';dest=tmp_path/'restored.db'
    backup(app.config['DATABASE'],archive,key)
    assert not archive.read_bytes().startswith(b'SQLite')
    restore(archive,dest,key)
    with sqlite3.connect(dest) as db:assert db.execute('SELECT email FROM users').fetchone()[0]=='owner@example.test'
    with pytest.raises(ValueError):restore(archive,dest,key)
    with pytest.raises(InvalidToken):restore(archive,tmp_path/'wrong.db',Fernet.generate_key())
    assert not (tmp_path/'wrong.db').exists()
    assert retention_candidates(dest)==[]
