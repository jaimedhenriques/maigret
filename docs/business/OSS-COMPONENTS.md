# Open-source components and integration decisions

Source and license review performed on 2026-10-03 against the official GitHub
repositories below. This is a component shortlist, not evidence that a complete
regulated identity or employment-screening service is available from any one
repository. Code, trained models, datasets, trademarks, and hosted API rights
must each be checked separately.

## Code copied into Vetra

The Python implementation from
[Standard Webhooks](https://github.com/standard-webhooks/standard-webhooks) is
vendored at `vetra/vendor/standardwebhooks/`, with its **package-specific MIT
license**, exact source commit and SHA-256 file hashes retained. The monorepo
root has Apache-2.0 terms; the Python package has its own MIT `LICENSE` and
declares MIT in its `pyproject.toml`.

- Commit: `7537d2a2d3d52d8f2e0ecd12527af4a9307fd81b` (2026-08-31).
- Version: 1.1.0. Runtime dependencies: Python standard library only.
- Copied without changes: `webhooks.py`, `__init__.py`, `exceptions.py`,
  `py.typed`, and `LICENSE` from `libraries/python`.
- Attribution/provenance: `vetra/vendor/standardwebhooks/UPSTREAM.json` and
  `README.vetra.md`.
- Validation: all **15 official upstream Python tests** passed against the
  vendored files using the project virtual environment. Application-level
  integration tests are separate from this source verification.

Vetra actively imports the copied verifier in `vetra/workflow_ingress.py` for
`POST /api/webhooks/workflow`. The endpoint authenticates partner notifications,
binds the tenant/candidate/check references to recorded checks, persists delivery
IDs for deduplication, and gates processing on candidate consent. Notifications
are recorded as audit evidence; they do not change a check's status or become
verification attestations. A contracted provider and its result mapper are
required for that additional behavior. The dedicated integration tests cover
signed acceptance, tampering, freshness, malformed input, missing configuration,
reference binding, replay, withdrawal and preventing notifications from becoming
verified check results.

This reusable code signs and verifies the Standard Webhooks protocol: message
ID, timestamp, raw JSON body, HMAC SHA-256 signatures, constant-time comparison,
and a five-minute timestamp window. It supports authenticated integration with
providers that implement those headers. It supplies no biometric recognition,
document authenticity, or background data. Stripe's signature protocol is
different and continues to require its own verifier.

The receiver must enforce tenant/session binding, deduplication, allowed state
transitions, consent withdrawal and malformed-input rejection. The upstream
implementation can raise decoding or value errors for malformed input as well
as `WebhookVerificationError`; callers must reject all of these. Vendoring the
verifier does not, by itself, enable an additional screening provider.

## Shortlist

| Repository | License actually inspected | Useful capability | Evidence of activity and limits | Decision |
| --- | --- | --- | --- | --- |
| [Standard Webhooks](https://github.com/standard-webhooks/standard-webhooks) | Python package MIT; monorepo root Apache-2.0 | Provider callback signing/verification and interoperable event contract | Cloned source commit above; package 1.1.0; official tests inspected and run | Exact small Python component copied with notices; use for compatible provider integrations |
| [PassportEye](https://github.com/konstantint/PassportEye) | MIT, repository `LICENSE` and source headers | Locates and reads machine-readable zones in identity document images; parses MRZ fields and check digits | Cloned commit `c584943d49b5942c289f9ff019c157dee728057c`, 2026-07-03. README describes approximately 80% recognition on the developer's available examples, 10+ seconds for some scans, and limitations on blurred/nearby text. These are upstream descriptions, not validated production performance | Candidate for an isolated document extraction service. Do not equate MRZ/checksum consistency with authentic identity; not integrated |
| [OpenSanctions yente](https://github.com/opensanctions/yente) | MIT code, repository `LICENSE`; README separately identifies commercial data licensing | Self-hosted HTTP search and matching of people/company/watchlist entities; supports custom datasets | Cloned commit `28af9231b1865a121b2abb4228c249499dd74f3f`, 2026-10-01. Matching route and FastAPI source inspected. Requires Elasticsearch/OpenSearch plus data/index operations | Prefer a separately deployed API or commercial data contract. Keep source citations, dataset versions and human match resolution. No data downloaded and no screening activated |
| [Keycloak](https://github.com/keycloak/keycloak) | Apache-2.0, repository `LICENSE.txt` and README | Enterprise login, federation, strong authentication, user management and authorization | Official metadata: not archived, pushed 2026-10-03; README and full license fetched. No deployment, independent security assessment or configuration review performed | Integrate supported OIDC/SAML interfaces for customer SSO/MFA. Authentication infrastructure does not provide candidate identity proofing; not integrated |
| [DIF did-jwt-vc](https://github.com/decentralized-identity/did-jwt-vc) | Apache-2.0, repository `LICENSE` | Creates and verifies W3C credential/presentation JWTs; README demonstrates a university-degree credential | Official metadata: not archived, pushed 2026-10-03; README and full license fetched. Requires DID resolution and compatible credential formats | Useful future credential-verifier service when issuers support it. Signature validity still requires trusted issuer policy, subject binding, expiry/revocation and presentation challenge checks; not integrated |

Repository `pushed_at` metadata is activity evidence, not a maintenance guarantee
or a substitute for review of releases, security response and support. No
enterprise service-level commitments or accuracy claims were independently
validated for these projects.

## Repositories rejected for blanket copying

**[Ballerine](https://github.com/ballerine-io/ballerine)** has useful risk workflow,
case review, document collection and provider-orchestration ideas, but its
current official
[`LICENSE` at commit `8659a4be371b9137c6bb5369e21538b9a8d9de8c`](https://github.com/ballerine-io/ballerine/blob/8659a4be371b9137c6bb5369e21538b9a8d9de8c/LICENSE)
uses per-file/per-directory rules and **defaults to Elastic License 2.0**. That
license says: "You may not provide the software to
third parties as a hosted or managed service, where the service provides users
with access to any substantial set of the features or functionality of the
software." A competing hosted platform cannot simply copy the entire
repository under its included MIT text. Any individually MIT-licensed component
would need a separate file and dependency review. In addition, its README
explicitly states that the open source repository is undergoing a major rebuild
and is **not actively supported**. No Ballerine code copied.

**[FaceOnLive ID-Verification-OpenKYC](https://github.com/FaceOnLive/ID-Verification-OpenKYC)**
is a repository advertising an IDKit/SDK offering. The inspected GitHub
metadata returned no detected license; `LICENSE` and `LICENSE.md` did not exist
at the fetched paths. Its README promotes a paid server/SDK bundle. The public
repository name and marketing claims do not establish commercial redistribution
rights or independently validated liveness performance. Do not copy its SDKs,
binaries or models without explicit, suitable terms. No source copied.

## Integration order for a hiring product

1. Keep candidate consent, correction, withdrawal and audit workflows in Vetra.
   Activate a contracted identity provider through hosted capture and verified
   events; retain provider references rather than unnecessary raw ID images.
2. Use the vendored webhook component only where the provider supports the
   Standard Webhooks protocol. Add provider-specific event schemas, tenant
   binding and reconciliation before a result can become an attestation.
3. Add Keycloak or another supported enterprise identity service through OIDC
   for customer authentication. Complete application authorization and tenant
   isolation checks independently.
4. Evaluate PassportEye with representative permitted document samples in an
   isolated service if document extraction is needed. Preserve the distinction
   between extracted fields, manual review, and provider-authenticated identity.
5. Evaluate credential JWT verification with participating, trusted education
   or employment issuers. Support issuer/subject checks and revocation before
   presenting a credential as verified.
6. Activate sanctions or other screening only for contracted datasets and
   applicable hiring use cases. Preserve source evidence and resolve possible
   matches with appropriate human review and candidate procedures.

No listed repository supplies authoritative criminal history, right-to-work,
employment references or worldwide credential coverage merely by cloning it.
Those checks require suitable lawful sources, market-specific provider contracts
and operating procedures. The launch plan in `LAUNCH-PLAN.md` covers these gates.

## Local research material

Three upstream repositories were cloned for inspection under
`/workspace/oss-research/`: Standard Webhooks, PassportEye and yente. Official
README/license/metadata snapshots for the other candidates were fetched into
the same research directory. That directory is not part of the application
repository or deployment. No public GitHub forks were created: small compatible
code was vendored locally, and future independently deployed components can
follow their upstream releases without maintaining unnecessary forks.

Retain each copied component's copyright/license notices. Pin future production
dependencies, track vulnerabilities and updates, record model/data rights
separately, and re-review changed license terms before importing updates.
