# Verisento design toolchain

The user's required design sources are routed on every UI task by `AGENTS.md` and
`.agents/skills/verisento-interface/SKILL.md`. This is project guidance for every
contributor and delegated agent. It does not silently install a global policy into
unrelated projects, and it does not claim an inapplicable workflow ran.

## Reproducible source setup

The manifest pins all requested GitHub repositories to audited commits. Downloaded
source material and its SHA-256 locks stay in ignored `.design-toolchain/`; no
third-party code is executed by this setup script.

```bash
python scripts/design-tools.py list
python scripts/design-tools.py hydrate
python scripts/design-tools.py check
```

Use `--only <id> [<id> ...]` for a targeted download or verification. Review downloaded
scripts before running them. The manifest is a source inventory, not an install log
or proof that every workflow was executed.

## Read and apply one by one

All paths below are relative to `.design-toolchain/sources/` after hydration.

| Order | Source | Read first | Application |
|---|---|---|---|
| 1 | Product Design | Active plugin's index and focused workflow | Resolve the screen's job and current friction. Use the real app as the existing target. |
| 2 | Impeccable | `impeccable/.agents/skills/impeccable/SKILL.md` | Context, surface-specific playbook, craft floor, and bounded finish review. The active installed plugin remains authoritative for its own version. |
| 3 | UI/UX Pro Max | `ui-ux-pro-max/.claude/skills/ui-ux-pro-max/SKILL.md` | Search a coherent design system for large reworks or one explicit UX outcome for a small component. Detect the actual stack. |
| 4 | Apple Design / Emil Kowalski | `apple-design/skills/apple-design/SKILL.md` | Immediate press feedback, useful spatial transitions, type hierarchy, reduced motion and transparency. Gesture physics applies only to a gesture interaction. |
| 5 | TasteSkill | `taste-skill/skills/taste-skill/SKILL.md` | Current default is contextual and targets marketing/landing pages. It explicitly excludes dashboards, data tables and multistep product UI. Older v1 and GPT variants are preserved references, not simultaneous mandates. |
| 6 | Vercel Web Design Guidelines | `web-design-skill/skills/web-design-guidelines/SKILL.md` | Fetch the current Web Interface Guidelines before reviewing changed UI; the linked rules live in the separately MIT-licensed `web-interface-guidelines` repository. |
| 7 | Image-to-Code | `taste-skill/skills/image-to-code-skill/SKILL.md` | For major visual work with available generation, generate readable section references first, analyze them, then implement and compare. Technical-only fixes use its stated exception. |
| 8 | Figma MCP | Active Figma plugin's create/generate/design-to-code skill | Use callable Figma tools for requested mockups; return the actual file link. Document an access/tool limitation if creation is unavailable. A diagram is not a UI mockup. |
| 9 | Awesome Design | `awesome-design/README.md` | A catalog of design-system references, not an executable skill. Choose a relevant system, not an unrelated pile of visual styles. |
| 10 | shadcn/ui + user's fork | `shadcn/skills/shadcn/SKILL.md` and `shadcn-user-fork/skills/shadcn/SKILL.md` | Search, read docs and inspect source before a component change. Compare fork/upstream changes and preserve MIT notices when copying. |
| 11 | 21st.dev | Connected account, CLI help, and MCP tool schemas | Search the account for every reusable component task, inspect source/dependencies/license, then implement compatible code. See `21st-mcp.md` for account configuration and secret handling. |
| 12 | Anti-slop | `anti-slop/skills/antislop/SKILL.md` plus applicable subskills | Use during development under the user's standing request. Apply purpose tests and delivery gate; truthful data, real controls, useful states and responsive behavior are hard requirements. |
| 13 | SkillUI | `skillui/README.md` | Optional design extraction from our own code or an authorized reference. The checkout has no root license; npm metadata declares MIT. No repository code is vendored. |
| 14 | Screenshot-to-Code | `screenshot-to-code/README.md` | Optional standalone app when an authorized screenshot/Figma target warrants it. Requires model accounts; it is not a library to inject into production. |
| 15 | Website Cloner | `website-cloner/.agents/skills/clone-website/SKILL.md` | Use for a supplied source-cloning task. Observe real responsive layouts/interactions first and record source-to-local mapping; do not copy another company's claims or identity. |
| 16 | Playwright CLI | `playwright-cli/skills/playwright-cli/SKILL.md` | Desktop/mobile, keyboard, reduced-motion and workflow checks, with screenshots and actual evidence. Compatible browser automation must be recorded accurately if the CLI cannot run. |

## Components and stack compatibility

Verisento currently renders server templates with Flask/Jinja, native CSS and
JavaScript. shadcn registry components usually expect React, Tailwind and a primitive
library. A read-only search does not install those components. Adapt semantic HTML
and interaction patterns to the existing app where appropriate, or make an explicit
framework integration before importing TSX. Keep consent, CSRF and staff login
working. Never claim native markup is a Radix/shadcn installation.

Installed developer CLI versions are pinned in the manifest:

```bash
npm install -g @playwright/cli@0.1.22 shadcn@4.21.3 --ignore-scripts
playwright-cli --version
shadcn --version
shadcn search @shadcn -q "sidebar" --limit 4
shadcn docs button dialog table empty sheet
shadcn view @shadcn/button
```

The official CLI is used for component acquisition and docs. The user's fork is a
GitHub source repository, not an assumed public shadcn registry. The audited shadcn
skill in the fork matches upstream byte-for-byte; compare the actual component
file you intend to use rather than assuming all fork code is identical. The audited
Base UI Button source differs in its `cn` utility import, so a fork import path must
be adapted to the target project. CLI documentation currently selects Base UI while
an unconfigured `view @shadcn/button` can return the legacy Radix source. Choose and
verify one primitive base explicitly before installation; never mix their APIs.

After reviewing the downloaded Python scripts, a real Pro Max system search runs
without third-party Python dependencies:

```bash
python .design-toolchain/sources/ui-ux-pro-max/.claude/skills/ui-ux-pro-max/scripts/search.py \
  "HR verification SaaS trust" --design-system -p "Verisento" \
  --variance 4 --motion 2 --density 6 -f markdown
```

Treat search output as recommendations. Verify that the returned product and rules
fit HR verification; do not persist an off-topic result or claim a search succeeded
when it returned no match. Do not overwrite an accepted `DESIGN.md` with generated
defaults.

## Conflict and licensing rules

User instructions, truthful product evidence, accessibility and the accepted design
direction win over contradictory external style recipes. One version of a given
skill leads each surface. No fake tool output or simulated RNG, invented metrics,
unsupported provider coverage, forced perpetual animation, or framework migration
solely to satisfy an old example.

Most requested repositories carry MIT or Apache-2.0 licenses. The source manifest
records the audit result. `vercel-labs/agent-skills` and `amaancoderx/npxskillui` do
not have a root license file in the audited checkout; their references are read
locally, and no source from those repositories is redistributed here. README/npm
license claims are recorded separately from a verified repository license. The
fresh Vercel rules are available from MIT-licensed `vercel-labs/web-interface-guidelines`.
The licenses of referenced brands, assets, community components and generated code
still require their own review.

## Delivery evidence

Every UI handoff should record the changed surfaces, actual visual references/Figma
link, component search/provenance, applied checks, test/browser evidence, and blocked
capabilities. Distinguish **applied**, **inspected**, **not applicable**, and
**unavailable**. Do not say all tools ran merely because they were configured.
Use a batched desktop/mobile inspection, one fix batch and one confirmation pass.
Auth cookies, screenshots containing real candidate data and provider keys stay out
of commits and external design-service prompts.
