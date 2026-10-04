# Paid HR pilot setup

## Current status

Software foundation is deployed; commercial activation is blocked by brand approval, legal operator details, account creation, live credentials and operational sign-off. No outreach is being sent. The owner has stated the product is not ready for GTM.

Initial sales segment: UK recruitment agencies. Global architecture means country-specific coverage, notices, retention and contractual review; it does not mean all checks are universally available. Start with candidate-controlled identity, employment and education checks. Do not advertise automated employment/education verification or criminal-check coverage that is not contracted and tested.

## Accounts to create after brand approval

1. Register the approved domain. Complete company details, privacy/support contacts, contracts and privacy review.
2. Create the operator's account at https://dashboard.stripe.com/register and complete business onboarding, bank setup and Stripe Identity enablement. These steps require the business owner and accurate legal details. Configure live credentials directly in Railway; do not send secret keys in chat.
3. Create a fixed pilot fee in Stripe Products (agree price, scope, tax treatment, refunds and invoice requirements first). Set STRIPE_PILOT_PRICE_ID, STRIPE_SECRET_KEY and STRIPE_BILLING_WEBHOOK_SECRET. The application supports a one-time fee, not recurring subscriptions. Checkout shows the agreed Stripe price. Bind payment to the workspace, and recognize payment only through a signed webhook. Manual invoice reconciliation remains a valid initial pilot option.
4. Identity webhook: `/api/webhooks/stripe`, events described in PROVIDER-INTEGRATIONS.md. Billing webhook: `/api/webhooks/billing`, subscribe to checkout.session.completed, checkout.session.async_payment_succeeded, checkout.session.async_payment_failed and checkout.session.expired. Use separate signing secrets.
5. Create transactional email account (e.g. https://postmarkapp.com). Verify sender domain with SPF/DKIM and configure SMTP_HOST, SMTP_PORT=587, SMTP_USERNAME, SMTP_PASSWORD and VETRA_EMAIL_FROM. Send invitation and recovery tests to owned addresses; verify inbox placement. Server acceptance is not proof of inbox delivery. Delivery is synchronous in this pilot; bounce processing, retries/queues and monitoring are pending.
6. Fill VETRA_LEGAL_NAME, VETRA_LEGAL_ADDRESS, VETRA_PRIVACY_EMAIL, and agree VETRA_RETENTION_DAYS. `/privacy` remains explicitly a draft until completed; get a qualified review of controller/processor roles and candidate notices.

## Operational verification before real candidates

- Test owned identity documents with provider permission: consent required, success, rejected documents, cancellation, repeat webhooks, wrong tenant/session, corrections and withdrawal/redaction. Local provider protocol tests cover these paths; a live acceptance run is still needed.
- Verify payment success, failed/asynchronous payment, replay, cross-tenant metadata mismatch, refunds and receipts. Refunded payments currently need operator reconciliation; no automated entitlement or refund handling is claimed.
- Recover an account through email; link expires after 30 minutes, can be used once, and revokes previous staff sessions. Five failed sign-ins are rate limited. Recovery requests are limited per normalized email.
- Use isolated workspaces per pilot client; never put separate customers into one tenant. Provisioning/self-service signup is not implemented: use a reviewed administrative onboarding process or separate pilot service until multi-customer onboarding is ready.
- Schedule encrypted online backups with `python -m vetra.operations backup --file /secure-export/snapshot.backup`; store VETRA_BACKUP_KEY separately from the archive and upload archives to a restricted off-site bucket. An archive on the same Railway volume is not disaster recovery. Set a seven-day backup expiry unless the agreed policy requires another duration. Configure Railway volume backups too, then test restore into a new stopped service with `python -m vetra.operations restore --database /restore/vetra.sqlite3 --file snapshot.backup`. Integrity and foreign keys are checked; restore refuses existing targets. Local encrypted backup/restore is tested; production scheduling, off-site transfer, and production restore drills are not yet enabled.
- Run `python -m vetra.operations retention-report --days 90`. This is a dry-run identifying completed/withdrawn records; no automatic deletion is enabled. Check legal holds, request identity-provider redaction, remove/anonymize candidate evidence and contact data under a reviewed procedure, and expire backups. Append-only audit design needs a separate agreed audit-retention policy before commercial operation.

## Employment and education procedure

Candidate supplies dates, organization/institution, role/qualification and an authorized verifier reference. Obtain approval before contact. Independently validate the official organization/institution channel; do not rely solely on candidate-supplied contact details. Use minimal questions, record response date, source and reviewer, distinguish verified source responses from unverified candidate claims, and offer a correction route. Vetra labels these as **manual reviews**, never identity-provider attestations. For scaled coverage, contract credential providers after country, institution coverage and data-processing review. Criminal records and right-to-work checks remain outside this pilot; UK DBS checks involve eligibility and a qualified route.

## Pilot measurement and future recruitment

`/pilot` reports real case counts, completion rate, average consent-to-completion hours, payment state and reported HR time saved. Time savings are entered per consented case using an actual comparable baseline; no invented ROI. Completion includes manual review, not a hiring recommendation. Agree target metrics before launch: e.g. >=80% candidate completion, measured turnaround, correction resolution time, and baseline HR effort. After readiness sign-off, recruit three agencies through owner-approved outreach, using SALES-KIT.md. No customer contacts or outreach authorization are available yet.
