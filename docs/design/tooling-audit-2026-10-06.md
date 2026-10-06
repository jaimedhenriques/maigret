# Design tooling setup evidence

Audited on 2026-10-06 for the Verisento redesign. This records tooling work, not
completion of every design workflow or commercial launch requirements.

## Completed setup

- All 14 requested GitHub source repositories resolved. Exact commit revisions,
  license findings, source entrypoints and package integrity values are recorded in
  `tooling-sources.json`.
- Hydrated 209 pinned source/reference files into ignored `.design-toolchain/` and
  verified their recorded SHA-256 checksums. The hydration script does not execute
  remote instructions or install packages.
- Installed official `@playwright/cli@0.1.22` and `shadcn@4.21.3` globally with npm
  lifecycle scripts disabled. Verified both CLI version outputs.
- Added repository instructions and a local interface skill requiring source-by-source
  routing on future UI work, including delegated agents.

## Actual searches and inspected source

UI/UX Pro Max was run after inspecting its Python entrypoint and local read/write
behavior. The query `HR verification SaaS trust` returned **Trust & Authority +
Conversion** and **Minimalism & Swiss Style**, with dials variance 4, motion 2,
density 6. The first typography result was an editorial mismatch and was rejected.
A narrower `enterprise dashboard readable sans` typography query returned **Corporate
Trust** (Lexend + Source Sans 3) and **Enterprise SaaS Mobile** (Plus Jakarta Sans).
These are optional recommendations; they do not overwrite the accepted brand system.
Logo/certification proof suggestions require real evidence and are not permission to
invent proof.

The focused `error summary validation` query returned a focusable error summary,
links to invalid fields, preserved inline errors, and error announcements. Those
recommendations fit the candidate/staff form workflow.

Official shadcn CLI search found 31 sidebar results. `docs` returned current
Button, Dialog, Table, Empty and Sheet documentation URLs. Their markdown docs were
fetched, and `view` retrieved actual Button, Dialog, Empty and Table source with
declared dependencies. These are React/Tailwind components; they were researched
without injecting TSX into the Flask application.

The user's fork and upstream share the same audited shadcn skill content. An actual
Base UI Button comparison found a utility import-path difference (`cn` versus the
fork's registry-relative alias). Component source must be inspected individually.
CLI docs defaulted to Base UI and the unconfigured registry view returned legacy
Radix source, so the integration must choose a primitive base explicitly.

## Browser CLI smoke check

Playwright CLI opened the deployed `/login` page in a named, isolated, headless
Chromium session using the available `/usr/bin/chromium` executable. The page title
was **Sign in · Verisento**, a login form was present, and there was no horizontal
overflow at 1440px. The session was closed. This is a tooling smoke check; the full
desktop/mobile/workflow review is separate redesign evidence.

## Scope and availability distinctions

- **Core UI guidance:** Impeccable, UI/UX Pro Max, Apple Design, Vercel guidelines,
  and anti-slop were inspected and configured for ongoing use on relevant UI.
- **Marketing guidance:** current TasteSkill explicitly excludes dashboards,
  data tables and multistep product UI. Its current contextual version leads
  marketing work; old v1/GPT variants remain reference-only alternatives.
- **Mockup translation:** Image-to-Code requires generation-first visual references
  for substantial visual work when available. Figma work and 21st account activity
  are recorded separately in their own integration/design artifacts.
- **Design catalog:** Awesome Design is reference material rather than an executable
  plugin or component package.
- **Reference-only tools:** SkillUI, Screenshot-to-Code and Website Cloner were
  reviewed. Their standalone applications were not installed or run merely to
  redesign our own app. Extraction/cloning requires a suitable authorized source;
  Screenshot-to-Code also requires model-provider accounts.
- **Licensing:** the audited `vercel-labs/agent-skills` and
  `amaancoderx/npxskillui` checkouts lack root license files. No repository code from
  them is redistributed. SkillUI's README/npm metadata declare MIT, which is recorded
  separately from a verified source license. The Vercel interface rules have a
  separately verified MIT-licensed source.

The guide mandates honest **applied**, **inspected**, **not applicable**, and
**unavailable** reporting. It does not promise all independent tools execute on
every component or that repository instructions affect unrelated machines.
