# Provider integrations

Vetra is a consent-based HR workflow with a Stripe Identity adapter. It does not
currently supply criminal records, education verification, employment verification,
sanctions screening, credit reports, or government right-to-work attestations.
Those capabilities remain **not connected**. Maigret username searches are not
identity verification or a substitute for a legally obtained background report.

## Stripe Identity

The adapter in `vetra/providers.py` uses the Python standard library and Stripe's
hosted document flow. It creates a document verification session with a matching
selfie requirement, tenant/candidate/check metadata, and an idempotency key.
Documents and selfies are collected by Stripe, not uploaded into Vetra. The HR
application stores the session identifier, short-lived hosted link, and result state.

Configure these secrets outside version control:

```text
STRIPE_SECRET_KEY=sk_live_...        # Or an appropriately scoped rk_live_... key
STRIPE_WEBHOOK_SECRET=whsec_...
VETRA_PUBLIC_URL=https://your-vetra-host.example
```

Register `https://your-vetra-host.example/api/webhooks/stripe` with Stripe for:

- `identity.verification_session.verified`
- `identity.verification_session.requires_input`
- `identity.verification_session.processing`
- `identity.verification_session.canceled`

The Stripe account must have Identity enabled and support the intended geography,
document types, business use, and biometric processing. Provider contracting,
purpose review, candidate disclosure and regional consent requirements remain
deployment prerequisites. Document verification confirms the provider's specific
identity checks; it does not establish employment suitability or clear every risk.

The adapter fails closed without a key and webhook secret. It only accepts hosted
links on `https://verify.stripe.com`, never follows API redirects, and validates
session metadata and live/test mode in the create response. A returned or refreshed
browser page cannot set a check to verified.

For webhooks, HMAC-SHA256 is verified against the **raw** request bytes before JSON
decoding, with a 300-second past/future timestamp window and constant-time digest
comparison. The application then matches the provider session ID and all three
metadata identifiers against persisted records; it deduplicates event IDs, checks
event type against status, requires active consent, and ignores late downgrades.
Test-mode events cannot create a live attestation in the HR application. A signature
authenticates the delivery; it does not replace the application's tenant and
authorization checks.

Withdrawal removes the candidate's hosted link and attempts provider cancellation;
if cancellation fails, redaction is requested. A successful redaction request can
be asynchronous and is not proof of completed deletion. Failed cleanup is surfaced
for staff follow-up. Production needs a durable cleanup queue, confirmation of
redaction completion and reconciliation of undelivered events.

## Honest environments

The separate `DemoProvider` only returns explicit sample data with
`attestation=False`. It cannot start a real verification. Fictional demonstration
candidates must never be submitted to an external provider. Use Stripe test keys
and test documents in an isolated staging environment; the live HR route requires
a live provider and real consent. Unit tests use synthetic signed fixtures and a
fake transport; they do not demonstrate live account connectivity.

Before a live pilot, verify account eligibility, hosted session creation, signed
webhook delivery, repeated delivery, interrupted sessions, consent withdrawal,
redaction completion, mismatched metadata, test/live separation and support recovery
using provider test facilities and then approved live checks. No live Stripe
connection has been exercised as part of this implementation.

## Background screening contract

The project also integrates the vendored MIT licensed Standard Webhooks Python
verifier for a separate endpoint, /api/webhooks/workflow. Configure
VETRA_WORKFLOW_WEBHOOK_SECRET with whsec_ followed by base64 of at least 32 random
bytes. Send webhook-id, webhook-timestamp and webhook-signature headers in the
Standard Webhooks format. The signed JSON envelope contains type (check.updated
or check.completed) and data with tenant_id, candidate_id and check_id. The receiver
binds those references to a persisted check, deduplicates delivery IDs and checks
candidate approval. It records an authenticated notification only: it cannot mark a
check verified or turn an external status string into a screening result.

A contracted provider-specific result mapping, provenance and dispute process are
required before background verification outcomes can enter the product. Standard
Webhooks and Stripe signatures are different protocols and use separate secrets.
See the vendor UPSTREAM.json and OSS-COMPONENTS.md for the exact copied version,
component license and source hashes. Raw notification bodies are not retained.

Connect licensed or otherwise authorized sources with a separate adapter per
jurisdiction and check type. Do not scrape criminal records or reuse social profiles
as identity proof. Each adapter should expose:

| Operation | Required behavior |
| --- | --- |
| Capability discovery | Explicit supported geographies, sources, contract availability and unavailable checks |
| Create order | Consent/disclosure evidence, purpose, scoped identifiers and idempotency key |
| Receive result | Signed delivery or authenticated polling; order/tenant/candidate binding; no inferred clearance |
| Review | Original source provenance, uncertainty, human adjudication and correction/dispute path |
| Cancel/delete | Stop collection, apply lawful retention, durable retries and completion confirmation |

Use distinct states such as `not_connected`, `awaiting_consent`, `in_progress`,
`requires_input`, `provider_completed`, `needs_review` and `canceled`. Preserve the
difference between verified identity, reviewed evidence and a hiring decision. A
manual review is labeled manual and never promoted to provider-attested verification.

## References and source provenance

- Stripe session creation: https://docs.stripe.com/api/identity/verification_sessions/create
- Stripe webhook signatures: https://docs.stripe.com/webhooks/signature
- Stripe session cancellation: https://docs.stripe.com/api/identity/verification_sessions/cancel
- Stripe session redaction: https://docs.stripe.com/api/identity/verification_sessions/redact

The Stripe adapter is new project code implementing the documented protocol; no
Stripe SDK was copied. The separate partner notification receiver uses the copied
Standard Webhooks verifier described above. Documentation URLs are supplied for
operator review. Automated retrieval of those pages was blocked in this workspace,
so verify provider configuration and API behavior against current documentation
before connecting an account.
