# Verisento project instructions

This repository contains the Verisento HR verification app in `vetra/`, a static
Vercel frontend build in `frontend/`, and the original Maigret engine. Preserve
candidate consent, tenant scope, staff authorization, correction rights, truthful
provider status, and the separation between screening evidence and hiring decisions.

## Required design workflow

The user requires the requested UX/UI skills and component sources to be considered
on every design task, including marketing pages, app screens, and small components.
All contributors and delegated agents must read
`.agents/skills/verisento-interface/SKILL.md` before UI work, then the relevant
upstream instructions listed in `docs/design/tooling-sources.json`. Follow the
one-by-one routing checklist in `docs/design/tooling.md`; record which sources were
applied, inspected only, unavailable, or outside the current surface's scope.

Read `PRODUCT.md`, `DESIGN.md`, and a matching surface brief when present. Use the
actual running app and approved mockup as visual evidence. Never claim a tool was
used just because it appears in the manifest. A tool blocked by account access must
be reported accurately; continue the independently authorized work.

For substantial new visual directions, create and inspect design references before
coding. Use Figma MCP for requested mockups when callable, and follow the active
Image-to-Code workflow when visual generation is available. Preserve the working
product's real routes and workflows rather than replacing them with a mock app.

Search the connected 21st.dev account and the official shadcn registry before
building a reusable component. Inspect the user's `jaimedhenriques/ui` fork as an
additional source, checking differences and licenses before adaptation. Keep
21st credentials in local secret storage/environment variables only. Current
production UI uses Flask/Jinja and native CSS/JavaScript; React-only registry code
requires an intentional, compatible integration. Do not label a native adaptation
as an installed React component.

Apply Apple Design to immediate feedback, typography, spatial continuity, and
accessible motion. Apply current TasteSkill to marketing surfaces within its stated
scope. Apply Impeccable, UI/UX Pro Max, Vercel Web Interface Guidelines, and anti-slop
checks to all changed UI. Screen-to-code and website-cloning tools apply to an
explicit visual reference or an authorized source-cloning task, not arbitrary
third-party brand copying.

User instructions, real product facts, accessibility, privacy, and the accepted
design direction take precedence over contradictory stylistic defaults in external
sources. Do not simulate tool output, invent customer logos/testimonials, manufacture
metrics, add motion only to satisfy a recipe, or silently migrate frameworks.

Use a bounded Playwright review: desktop and mobile, keyboard navigation, reduced
motion, long content, empty/loading/error states, and key workflows. Fix the findings
in one batch, confirm once, and report relevant limitations and evidence.

These instructions persist for this repository and its agents. Other projects need
their own installed guidance; this file does not change another project's runtime.

<!-- antislop:start -->
## Anti-slop routing

The user's explicit request installs and requires anti-slop during UI development.
Read `.design-toolchain/sources/anti-slop/skills/antislop/SKILL.md`, then the UI,
human/accessibility, mobile layout, and copywriting subskills appropriate to the edit.
Apply the purpose test and delivery gate alongside the accepted product direction.
The user's authorization covers design mockups and the current rework; it does not
authorize fabricated social proof, real-person avatars, or unsupported product claims.
<!-- antislop:end -->
