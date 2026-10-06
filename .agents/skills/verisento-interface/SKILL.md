---
name: verisento-interface
description: Required project workflow for Verisento marketing, application UI, and components. Routes the user-requested design skills, Figma mockups, 21st.dev and shadcn research, and browser verification by actual scope.
---

# Verisento interface workflow

Read `AGENTS.md`, `PRODUCT.md` and `DESIGN.md` when present. The user wants a major
UX/UI improvement and ongoing use of the named design tools. This skill makes that
requirement durable without asserting every external tool applies to every task.

1. **Identify the job.** State the user, surface, primary task, current friction,
   product truth, and redesign scope. Staff screens help a reviewer decide the next
   verification action; candidate screens make consent and progress understandable.
2. **Read sources one by one.** Run `python scripts/design-tools.py list`. Hydrate
   missing pinned sources with `python scripts/design-tools.py hydrate`. Read the
   relevant upstream entrypoints from `docs/design/tooling.md`. This only downloads
   source material; it never installs packages or executes third-party code.
3. **Choose direction before implementation.** Use Product Design and Impeccable to
   inspect current evidence, then UI/UX Pro Max and Apple Design to resolve hierarchy,
   interaction, typography, and accessible behavior. Apply TasteSkill to marketing
   pages. Write why each palette, radius, layout, and motion choice serves the user.
4. **Produce the mockup.** For substantial visual redesign, generate and inspect
   readable design references, use Figma MCP where requested and callable, and record
   the Figma link or local artifact. Follow the active Image-to-Code requirements.
   Use clearly labelled fictional preview data in mockups only.
5. **Research components before writing them.** Search 21st.dev through the connected
   account, then official shadcn and the user's fork; inspect the returned source,
   dependencies, license, accessibility semantics, and current API docs. Keep source
   provenance. Native HTML/CSS adaptations and actual React installations must be
   described distinctly. Never pass candidate data or credentials to design services.
6. **Implement real flows.** Preserve authorization and consent, provide useful first
   run and filtered-empty states, keep errors actionable, and show reliable progress.
   Use named tokens, visible focus, semantic controls, keyboard alternatives, and
   reduced-motion/reduced-transparency fallbacks. Avoid repeated decorative cards and
   fake proof. If a paywall is temporarily disabled, preserve staff login and provider
   setup controls and make access mode clear.
7. **Verify and deliver.** Refresh Vercel's Web Interface Guidelines before review.
   Apply anti-slop core plus the relevant subskills, then run desktop/mobile and
   keyboard/reduced-motion checks using Playwright CLI or an explicitly recorded
   compatible browser runner. Compare the result with its visual source, fix concrete
   findings once, and confirm once. Report paths/URLs, performed checks, source use,
   and any account or licensing blockers without claiming unfinished actions.

Use `docs/design/tooling.md` for exact entrypoints, setup commands, applicability,
component acquisition, and honest status reporting.
