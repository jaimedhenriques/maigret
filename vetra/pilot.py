"""Commercial pilot operations; integrations fail closed until configured."""
import hashlib
import json
import os
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from urllib.parse import urlencode
from urllib.request import Request, build_opener
from urllib.error import HTTPError, URLError

from flask import Blueprint, current_app, g, jsonify, render_template, request, session, redirect
from werkzeug.security import generate_password_hash
from .store import audit, get_db, now_iso
from .providers import StripeIdentityProvider, ProviderError, _NoRedirect

bp = Blueprint('pilot', __name__)
SCHEMA = '''
CREATE TABLE IF NOT EXISTS password_resets(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),expires_at TEXT NOT NULL,used_at TEXT);
CREATE TABLE IF NOT EXISTS recovery_limits(subject TEXT PRIMARY KEY,requested_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS pilot_payments(session_id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL REFERENCES tenants(id),status TEXT NOT NULL,created_at TEXT NOT NULL,paid_at TEXT);
CREATE TABLE IF NOT EXISTS billing_events(event_id TEXT PRIMARY KEY,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS pilot_time_logs(id INTEGER PRIMARY KEY,tenant_id TEXT NOT NULL REFERENCES tenants(id),candidate_id TEXT NOT NULL,minutes INTEGER NOT NULL,baseline_minutes INTEGER NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(candidate_id,tenant_id) REFERENCES candidates(id,tenant_id));
'''


def email_ready():
    return all(os.environ.get(k) for k in ('SMTP_HOST','SMTP_USERNAME','SMTP_PASSWORD','VETRA_EMAIL_FROM')) and bool(current_app.config.get('PUBLIC_URL','').startswith('https://'))


def send_email(to, subject, body):
    """Synchronous bounded delivery; no message bodies or bearer links are logged."""
    if not email_ready():
        return False
    try:
        message = EmailMessage()
        message['From'] = os.environ['VETRA_EMAIL_FROM']
        message['To'] = to
        message['Subject'] = subject
        message.set_content(body)
        with smtplib.SMTP(os.environ['SMTP_HOST'], int(os.environ.get('SMTP_PORT','587')), timeout=10) as smtp:
            smtp.ehlo(); smtp.starttls(context=ssl.create_default_context()); smtp.ehlo()
            smtp.login(os.environ['SMTP_USERNAME'], os.environ['SMTP_PASSWORD'])
            smtp.send_message(message)
        return True
    except (OSError, smtplib.SMTPException, ValueError):
        return False


def deliver_invitation(candidate, path):
    if current_app.config['DEMO']:
        return 'manual'
    url = current_app.config['PUBLIC_URL'].rstrip('/') + path
    sent = send_email(candidate['email'], 'Your candidate verification invitation',
                      f"{g.user['organization']} invited you to review the scope of a hiring verification request.\n\nParticipation begins only after you approve the request. You can request corrections or withdraw.\n\n{url}\n\nThis link is personal. Do not forward it. It expires after seven days.")
    with get_db():
        audit(candidate['tenant_id'], 'invitation.email_sent' if sent else 'invitation.manual_delivery',
              'Invitation accepted by mail server' if sent else 'Copy invitation link; email not sent', candidate['id'], g.user['id'])
    return 'email' if sent else 'manual'


def staff(owner=False):
    return g.user is not None and (not owner or g.user['role']=='owner')


@bp.route('/forgot-password', methods=['GET','POST'])
def forgot_password():
    message = None
    if request.method == 'POST':
        email = str(request.form.get('email','')).strip().lower()[:254]
        subject = hashlib.sha256(email.encode()).hexdigest()
        db = get_db(); cutoff = (datetime.now(timezone.utc)-timedelta(minutes=15)).isoformat(timespec='seconds')
        with db:
            db.execute('BEGIN IMMEDIATE')
            last = db.execute('SELECT requested_at FROM recovery_limits WHERE subject=?',(subject,)).fetchone()
            permitted = not last or last[0] < cutoff
            if permitted:
                db.execute('INSERT OR REPLACE INTO recovery_limits VALUES (?,?)',(subject,now_iso()))
            db.execute('DELETE FROM recovery_limits WHERE requested_at<?',(cutoff,))
            row = db.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone() if permitted else None
            token = secrets.token_urlsafe(32)
            if row and email_ready() and not current_app.config['DEMO']:
                db.execute('DELETE FROM password_resets WHERE user_id=?',(row['id'],))
                db.execute('INSERT INTO password_resets VALUES (?,?,?,NULL)',(hashlib.sha256(token.encode()).hexdigest(),row['id'],(datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat(timespec='seconds')))
        if row and email_ready() and not current_app.config['DEMO']:
            send_email(email,'Reset your Vetra password',current_app.config['PUBLIC_URL'].rstrip('/')+'/reset-password/'+token+'\n\nThis single-use link expires in 30 minutes. Ignore it if you did not request a reset.')
        message = 'If an account exists and email delivery is enabled, a reset link will be sent. If it does not arrive, contact your workspace owner.'
    return render_template('account.html',title='Reset your password',kind='request',message=message,csrf_token=session['csrf'])


@bp.route('/reset-password/<token>',methods=['GET','POST'])
def reset_password(token):
    db=get_db(); digest=hashlib.sha256(token.encode()).hexdigest()
    row=db.execute('SELECT * FROM password_resets WHERE token_hash=? AND used_at IS NULL AND expires_at>?',(digest,now_iso())).fetchone()
    if not row:
        return render_template('account.html',title='Reset link expired',kind='done',message='Request a new password reset link.',csrf_token=session['csrf']),400
    error=None
    if request.method=='POST':
        password=request.form.get('password','')
        if not 12<=len(password)<=256:
            error='Choose a password with 12 to 256 characters.'
        else:
            with db:
                db.execute('BEGIN IMMEDIATE')
                changed=db.execute('UPDATE password_resets SET used_at=? WHERE token_hash=? AND used_at IS NULL AND expires_at>?',(now_iso(),digest,now_iso()))
                if changed.rowcount!=1:
                    return jsonify(error='Reset link expired.'),400
                db.execute('UPDATE users SET password_hash=?,auth_version=auth_version+1 WHERE id=?',(generate_password_hash(password),row['user_id']))
                user=db.execute('SELECT tenant_id FROM users WHERE id=?',(row['user_id'],)).fetchone()
                audit(user['tenant_id'],'password.reset','Staff password reset; previous sessions revoked',actor_id=row['user_id'])
            session.clear();session['csrf']=secrets.token_urlsafe(32)
            return render_template('account.html',title='Password updated',kind='done',message='Sign in with your new password.',csrf_token=session['csrf'])
    return render_template('account.html',title='Choose a new password',kind='reset',message=error,csrf_token=session['csrf'])


def billing_ready():
    return bool(os.environ.get('STRIPE_SECRET_KEY','').startswith(('sk_live_','rk_live_')) and os.environ.get('STRIPE_PILOT_PRICE_ID','').startswith('price_') and os.environ.get('STRIPE_BILLING_WEBHOOK_SECRET','').startswith('whsec_') and current_app.config['PUBLIC_URL'].startswith('https://'))


@bp.get('/pilot')
def pilot_page():
    if not staff():
        return redirect('/login')
    db=get_db(); tenant=g.user['tenant_id']
    counts=dict(db.execute('SELECT status,COUNT(*) FROM candidates WHERE tenant_id=? AND sample=0 GROUP BY status',(tenant,)).fetchall())
    durations=[r[0] for r in db.execute("SELECT (julianday(updated_at)-julianday(consent_at))*24 FROM candidates WHERE tenant_id=? AND sample=0 AND status='completed' AND consent_at IS NOT NULL",(tenant,))]
    times=db.execute('SELECT COALESCE(SUM(baseline_minutes-minutes),0),COUNT(*) FROM pilot_time_logs WHERE tenant_id=?',(tenant,)).fetchone()
    paid=db.execute("SELECT 1 FROM pilot_payments WHERE tenant_id=? AND status='paid' LIMIT 1",(tenant,)).fetchone()
    return render_template('pilot.html',csrf_token=session['csrf'],owner=g.user['role']=='owner',billing=billing_ready(),email=email_ready(),paid=bool(paid),counts=counts,total=sum(counts.values()),hours=round(sum(durations)/len(durations),1) if durations else None,saved=times[0],measurements=times[1])


@bp.post('/api/pilot/time')
def log_time():
    if not staff() or g.user['role']=='viewer':return jsonify(error='Reviewer access required.'),403
    body=request.get_json(silent=True) or {}
    if not isinstance(body,dict):return jsonify(error='JSON object required.'),400
    cid=body.get('candidate_id')
    minutes=body.get('minutes'); baseline=body.get('baseline_minutes')
    if type(minutes)!=int or type(baseline)!=int or not 0<=minutes<=10080 or not 0<=baseline<=10080:return jsonify(error='Enter measured and baseline minutes between 0 and 10080.'),400
    db=get_db()
    if not db.execute("SELECT 1 FROM candidates WHERE tenant_id=? AND id=? AND sample=0 AND consent=1 AND status!='withdrawn'",(g.user['tenant_id'],cid)).fetchone():return jsonify(error='Consented case not found.'),404
    with db:db.execute('INSERT INTO pilot_time_logs(tenant_id,candidate_id,minutes,baseline_minutes,created_at) VALUES (?,?,?,?,?)',(g.user['tenant_id'],cid,minutes,baseline,now_iso()))
    return jsonify(ok=True)


@bp.post('/api/billing/checkout')
def checkout():
    if not staff(True):return jsonify(error='Workspace owner access required.'),403
    if current_app.config['DEMO'] or not billing_ready():return jsonify(error='Live billing is not configured. Contact your workspace owner.'),503
    base=current_app.config['PUBLIC_URL'].rstrip('/')
    fields={'mode':'payment','line_items[0][price]':os.environ['STRIPE_PILOT_PRICE_ID'],'line_items[0][quantity]':'1','success_url':base+'/pilot?payment=returned','cancel_url':base+'/pilot','client_reference_id':g.user['tenant_id'],'metadata[tenant_id]':g.user['tenant_id']}
    # Checkout displays the agreed price; payment is recognized only by a signed webhook.
    req=Request('https://api.stripe.com/v1/checkout/sessions',data=urlencode(fields).encode(),headers={'Authorization':'Bearer '+os.environ['STRIPE_SECRET_KEY'],'Content-Type':'application/x-www-form-urlencoded','Idempotency-Key':'vetra-pilot-'+g.user['tenant_id']+'-'+secrets.token_hex(12)},method='POST')
    try:
        with build_opener(_NoRedirect()).open(req,timeout=15) as response:result=json.loads(response.read(65537))
        if not result.get('livemode') or not result.get('id','').startswith('cs_live_') or not StripeIdentityProvider._valid_https_url(result.get('url'),hosted=False) or __import__('urllib.parse',fromlist=['urlsplit']).urlsplit(result['url']).hostname!='checkout.stripe.com':raise ValueError()
    except (HTTPError,URLError,OSError,ValueError,KeyError):return jsonify(error='Payment service unavailable. Try again later.'),502
    with get_db():get_db().execute('INSERT INTO pilot_payments VALUES (?, ?, ?, ?, NULL)',(result['id'],g.user['tenant_id'],'pending',now_iso()))
    return jsonify(url=result['url'])


@bp.post('/api/webhooks/billing')
def billing_webhook():
    provider=StripeIdentityProvider(os.environ.get('STRIPE_SECRET_KEY',''),os.environ.get('STRIPE_BILLING_WEBHOOK_SECRET',''))
    if not billing_ready():return jsonify(error='Billing not configured.'),503
    try:event=provider.verify_webhook(request.get_data(),request.headers.get('Stripe-Signature',''))
    except ProviderError:return jsonify(error='Invalid signature.'),400
    if event['type'] not in ('checkout.session.completed','checkout.session.async_payment_succeeded','checkout.session.async_payment_failed','checkout.session.expired'):return jsonify(received=True)
    obj=event['data'].get('object',{})
    if not isinstance(obj,dict) or not isinstance(obj.get('metadata',{}),dict):return jsonify(error='Invalid event.'),400
    db=get_db()
    with db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT 1 FROM billing_events WHERE event_id=?',(event['id'],)).fetchone():return jsonify(received=True)
        row=db.execute('SELECT * FROM pilot_payments WHERE session_id=?',(obj.get('id'),)).fetchone()
        if not row or obj.get('client_reference_id')!=row['tenant_id'] or (obj.get('metadata') or {}).get('tenant_id')!=row['tenant_id'] or obj.get('mode')!='payment' or obj.get('livemode') is not True:return jsonify(error='Unbound checkout.'),400
        paid=obj.get('payment_status')=='paid' and event['type'] in ('checkout.session.completed','checkout.session.async_payment_succeeded')
        if row['status']!='paid':db.execute('UPDATE pilot_payments SET status=?,paid_at=? WHERE session_id=?',('paid' if paid else 'pending' if event['type']=='checkout.session.completed' else 'failed',now_iso() if paid else None,obj['id']))
        db.execute('INSERT INTO billing_events VALUES (?,?)',(event['id'],now_iso()))
        audit(row['tenant_id'],'billing.event','Pilot fee payment confirmed' if paid else 'Checkout status updated',actor_type='provider')
    return jsonify(received=True)


@bp.get('/privacy')
def privacy():
    return render_template('privacy.html',legal_name=os.environ.get('VETRA_LEGAL_NAME',''),address=os.environ.get('VETRA_LEGAL_ADDRESS',''),contact=os.environ.get('VETRA_PRIVACY_EMAIL',''),retention=os.environ.get('VETRA_RETENTION_DAYS','90'))


def init_pilot(app):
    with app.app_context():
        db=get_db();db.executescript(SCHEMA)
        if 'auth_version' not in {r['name'] for r in db.execute('PRAGMA table_info(users)')}:
            db.execute('ALTER TABLE users ADD COLUMN auth_version INTEGER NOT NULL DEFAULT 0')
        db.commit()
    app.register_blueprint(bp)
