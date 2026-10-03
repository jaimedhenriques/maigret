# Standard Webhooks Python source

Copied unmodified from `standard-webhooks/standard-webhooks`, commit
`7537d2a2d3d52d8f2e0ecd12527af4a9307fd81b`, package version 1.1.0.
The Python package has its own MIT license, retained in `LICENSE`; the
monorepo root has a different license. Exact file hashes are in `UPSTREAM.json`.
There are no runtime dependencies outside the Python standard library.

Use `from vetra.vendor.standardwebhooks import Webhook, WebhookVerificationError`.
The application imports the verifier in `vetra/workflow_ingress.py` for
`POST /api/webhooks/workflow`. Authenticated notifications are recorded as audit
evidence, with reference binding, delivery deduplication and consent gating.
They never change check state or constitute a verification attestation.
Only providers sending the Standard Webhooks `webhook-id`, `webhook-timestamp`,
and `webhook-signature` headers use this verifier. Stripe uses a different format
and must keep its separate verifier. Signatures authenticate payload origin;
they do not prove identity, credentials, or suitability for hiring.

The implementation enforces a five minute timestamp window and constant-time
HMAC comparison. The receiver must additionally enforce replay/idempotency by
webhook ID, tenant binding, raw body size limits, provider state transitions,
and malformed-input handling. Upstream can raise `ValueError`, `UnicodeError`,
or base64 decode errors for malformed headers/body; callers must reject these
alongside `WebhookVerificationError`, and never treat them as successful checks.

Update this component deliberately: compare upstream changes, retain license
and notices, regenerate hashes, and run integration/security regression tests.
