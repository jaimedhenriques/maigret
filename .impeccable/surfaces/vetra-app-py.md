---
version: 1
slug: "vetra-app-py"
primary_target: "vetra/app.py"
related_targets: []
---

# Staff sign-in

Mode: Operate
Scope: `/login`, `_LOGIN_PAGE` in `vetra/app.py`; styled by `operations.css`.
Audience: staff with an existing account.
Job: sign in to an authorized workspace or follow the recovery route.
Primary action: sign in with work email and password.
Proof: recognizable brand, labeled fields, autocomplete and factual access note.
Constraints: authentication, CSRF and authorization stay required while billing is disabled. Shared account/legal CSS does not make every route an authentication surface.

## Direction contract

This records the agent-selected, code-led direction; no seed key or user-selected concept card is corroborated.

THESIS: Keep staff access clear and reliable inside the same visual family.
OWN-WORLD: Operations-specific warm paper, graphite/forest and Manrope in a centered bordered form.
STORY: Recognize the workspace → enter credentials → sign in or recover access; errors preserve a clear return to the form.
FIRST VIEWPORT: The compact account container shows wordmark, welcoming title, work email, password, recovery and full-width primary action.
FORM: Native labeled controls with autocomplete, required fields, visible focus, alert errors and enlarged mobile input text. No seed key was produced.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

Review evidence: `docs/design/FINISH-REVIEW.md`; this brief does not issue its own ship verdict.
