# Vetra implementation handoff

The current deliverable is a working local pilot and a foundation for a candidate verification SaaS. It is not an activated screening service or a certified enterprise deployment.

## Review it

Start the app with the README commands. The HR workspace is at / and the marketing page at /about. Create an invitation, open the private candidate link in another browser session, approve the scope, submit a statement, review it in HR, request a correction, resolve it, and withdraw. Only use sample data in demo mode.

The new app runs independently of the Maigret research engine. Public username discovery and AI profiling are not present in the HR product. Maigret's module and command names remain compatible with upstream; the customer-facing name and the new service command are Vetra.

## Required activation inputs

| Input | Purpose |
|---|---|
| Confirmed launch country and eligible check scope | Choose identity, employment, credential and screening providers and legal procedures |
| Cleared brand and domain | Use the working name commercially |
| Identity-provider account, API key and webhook secret | Activate real hosted identity checks |
| Credential and background-data provider contracts | Produce sourced attestations for the promised check types |
| Hosting domain, HTTPS, database and secret manager | Run a private authenticated pilot |
| Privacy notices, retention schedule and customer agreement | Define employer/candidate rights and responsibilities |
| Three design partners | Validate workflow, evidence quality, willingness to pay and support effort |

## Enterprise release gates

- Migrate pilot storage to managed Postgres with tenant isolation validated independently.
- Add enterprise SSO, MFA and lifecycle management; validate authorization on every resource.
- Add durable queues, retry/dead-letter handling, idempotent provider reconciliation and monitoring.
- Contract providers for each market and check type, including candidate disputes and required employer procedures.
- Define retention/deletion, recovery objectives, incident response, provider subprocessors and hosting region.
- Run an independent security review, restore drill, capacity test and operating procedures exercise.
- Add billing, entitlements, metered provider charges, email delivery and customer onboarding.
- Test candidate accessibility and support in the target languages with real design partners.

No marketing or contract should claim any gate is complete until its supporting evidence exists.

## What can be sold first

A scoped paid workflow pilot: candidate approval, information collection, provider-connected identity when activated, source-based credential review, corrections and auditable case handling. Sell the supported country and check scope explicitly. Provider fees and third-party screening costs are separate from proposed workflow subscription prices.
