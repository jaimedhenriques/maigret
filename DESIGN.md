---
name: Verisento
description: Warm paper, graphite and forest for clear hiring verification workflows.
colors:
  workspace-paper: "#f6f5f1"
  workspace-surface: "#fff"
  workspace-ink: "#202723"
  workspace-muted: "#626960"
  workspace-line: "#e3e5de"
  workspace-forest: "#245642"
  workspace-forest-hover: "#183e2f"
  workspace-mint: "#eaf0e8"
  workspace-amber: "#80581a"
  workspace-amber-tint: "#fbf3df"
  workspace-danger: "#963f35"
  workspace-focus: "#426e53"
  workspace-rail: "#1c3027"
  workspace-rail-brand: "#f3f5ef"
  workspace-rail-active: "#385543"
  workspace-rail-muted: "#bdcbb9"
  workspace-status-neutral: "#56604e"
  workspace-status-neutral-bg: "#f0f2ec"
  workspace-status-reviewed: "#285b3b"
  workspace-status-reviewed-bg: "#eaf0e4"
  workspace-status-verified: "#285875"
  workspace-status-verified-bg: "#e8f0f4"
  workspace-status-review: "#805818"
  workspace-status-progress: "#3b5968"
  workspace-status-progress-bg: "#ebf0f2"
  workspace-status-withdrawn: "#646863"
  workspace-status-withdrawn-bg: "#f0f1ee"
  landing-paper: "#f7f8f6"
  landing-surface: "#fff"
  landing-ink: "#182723"
  landing-forest: "#174d3b"
  landing-forest-hover: "#103d2e"
  landing-muted: "#56645e"
  landing-line: "#dce2dc"
  landing-status-review: "#7a521d"
  landing-status-review-bg: "#f5ecdf"
  landing-status-neutral: "#526158"
  landing-status-neutral-bg: "#edf0ec"
  operations-paper: "#f8f8f4"
  operations-surface: "#fff"
  operations-ink: "#19392f"
  operations-muted: "#657168"
  operations-forest: "#244b3b"
  operations-forest-hover: "#19392c"
  operations-line: "#dee4dc"
  operations-tint: "#edf3ec"
  operations-amber: "#785b28"
  operations-amber-tint: "#f6f0e4"
  operations-focus: "#719e67"
typography:
  workspace-title:
    fontFamily: "Manrope, Arial, sans-serif"
    fontSize: "29px"
    fontWeight: 750
    lineHeight: 1.3
    letterSpacing: "-.035em"
  workspace-body:
    fontFamily: "Manrope, Arial, sans-serif"
    fontSize: "14px"
    lineHeight: 1.6
  workspace-label:
    fontFamily: "Manrope, Arial, sans-serif"
    fontSize: "12px"
    fontWeight: 700
  candidate-title:
    fontFamily: "Manrope, Arial, sans-serif"
    fontSize: "30px"
    fontWeight: 750
    lineHeight: 1.35
    letterSpacing: "-.035em"
  landing-display:
    fontFamily: "Manrope, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "clamp(54px, 5.9vw, 84px)"
    fontWeight: 600
    lineHeight: 1.08
    letterSpacing: "-.04em"
  landing-headline:
    fontFamily: "Manrope, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "clamp(35px, 4vw, 52px)"
    fontWeight: 550
    lineHeight: 1.12
    letterSpacing: "-.035em"
  landing-body:
    fontFamily: "Manrope, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "16px"
    lineHeight: 1.6
  operations-title:
    fontFamily: "Manrope, system-ui, sans-serif"
    fontSize: "clamp(28px,4vw,38px)"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "-.03em"
  operations-body:
    fontFamily: "Manrope, system-ui, sans-serif"
    fontSize: "14px"
    lineHeight: 1.75
  account-title:
    fontFamily: "Manrope, system-ui, sans-serif"
    fontSize: "30px"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "-.03em"
rounded:
  status: "5px"
  operations-control: "7px"
  workspace-control: "8px"
  notice: "12px"
  panel: "14px"
spacing:
  compact: "8px"
  control: "12px"
  row: "16px"
  mobile-gutter: "20px"
  section-gap: "24px"
  panel-inset: "30px"
components:
  workspace-button-primary:
    backgroundColor: "{colors.workspace-forest}"
    textColor: "{colors.workspace-surface}"
    typography: "{typography.workspace-label}"
    rounded: "{rounded.workspace-control}"
    padding: "11px 15px"
  workspace-button-primary-hover:
    backgroundColor: "{colors.workspace-forest-hover}"
  workspace-button-secondary:
    backgroundColor: "{colors.workspace-surface}"
    textColor: "{colors.workspace-ink}"
    rounded: "{rounded.workspace-control}"
    padding: "11px 15px"
  workspace-button-danger:
    backgroundColor: "{colors.workspace-surface}"
    textColor: "{colors.workspace-danger}"
    rounded: "{rounded.workspace-control}"
    padding: "11px 15px"
  workspace-navigation-active:
    backgroundColor: "{colors.workspace-rail-active}"
    textColor: "{colors.workspace-surface}"
    rounded: "{rounded.workspace-control}"
    padding: "12px 11px"
  workspace-input:
    backgroundColor: "{colors.workspace-surface}"
    textColor: "{colors.workspace-ink}"
    rounded: "{rounded.workspace-control}"
    padding: "12px"
  workspace-panel:
    backgroundColor: "{colors.workspace-surface}"
    rounded: "{rounded.panel}"
  workspace-status-review:
    backgroundColor: "{colors.workspace-amber-tint}"
    textColor: "{colors.workspace-status-review}"
    rounded: "{rounded.status}"
    padding: "5px 8px"
  landing-button-primary:
    backgroundColor: "{colors.landing-forest}"
    textColor: "{colors.landing-surface}"
    rounded: "{rounded.workspace-control}"
    padding: "14px 22px"
  landing-button-primary-hover:
    backgroundColor: "{colors.landing-forest-hover}"
  landing-button-outline:
    backgroundColor: "transparent"
    textColor: "{colors.landing-ink}"
    rounded: "{rounded.workspace-control}"
    padding: "14px 22px"
  landing-preview:
    backgroundColor: "{colors.landing-surface}"
    rounded: "{rounded.notice}"
  operations-button-primary:
    backgroundColor: "{colors.operations-forest}"
    textColor: "{colors.operations-surface}"
    rounded: "{rounded.operations-control}"
    padding: "11px 18px"
  operations-button-primary-hover:
    backgroundColor: "{colors.operations-forest-hover}"
  operations-input:
    backgroundColor: "{colors.operations-surface}"
    textColor: "{colors.operations-ink}"
    rounded: "{rounded.operations-control}"
    padding: "11px 12px"
---

# Design System: Verisento

## Overview

**Creative North Star: "A clear case file"**

Warm paper, graphite text and measured forest accents give the interface the character of a well-kept working file. Manrope, restrained borders and generous grouping keep information approachable at working density. This direction was agent-selected within the authorized redesign; these records extract the implementation, rather than claiming a user-selected concept card.

The system adjusts density and expression to each route. Surface strategy and visitor modes live in the [surface briefs](.impeccable/surfaces/). Product truth stays in [PRODUCT.md](PRODUCT.md); source use and process limits are recorded in [DESIGN-DELIVERY.md](docs/design/DESIGN-DELIVERY.md).

**Key Characteristics:**

- Warm light surfaces, graphite text and forest actions.
- Self-hosted Manrope throughout.
- Flat bordered containers and contextual tinted groups.
- Textual statuses, native controls and visible keyboard focus.
- Separate palettes and responsive rules for working, marketing and account surfaces.

## Colors

The frontmatter preserves exact source colors. Prefixes are documentation namespaces, not newly implemented CSS variables. Do not collapse these values into one universal palette.

### Primary

Workspace Forest maps to the internal `--teal`/`--teal-dark` names in [workspace.css](vetra/static/workspace.css), shared by HR and candidate pages. Landing Forest comes from [landing.css](vetra/static/landing.css). Operations Forest comes from [operations.css](vetra/static/operations.css), also used by login and shared account/legal styling.

### Neutral

Each palette has its own paper, ink, muted text, dividers and white surface. The workspace's dark rail uses the final rail override declarations, which supersede its earlier light-rail CSS. Marketing's illustration rail and dark scope section use Landing Ink; they do not share the production rail color.

### Status and feedback

Workspace review attention uses amber, manual review uses green and provider results use blue. Its review-badge foreground differs slightly from the queue amber token. Landing status tokens belong to a fictional illustration. Operations pending tags use its own amber; a green readiness tag can still say “Review needed.” Workspace danger and each surface's focus treatment remain distinct.

**The Surface Palette Rule.** Use the palette from the stylesheet that renders the surface; neighboring routes and Figma reference tokens do not silently redefine production values.

## Typography

**Display and Body Font:** self-hosted Manrope, variable weights (200–800), `font-display: swap`, supplied under the SIL Open Font License. Fallback stacks are recorded per surface above. No editorial serif pairing is implemented.

### Hierarchy

- **Display and headlines:** landing uses the fluid roles above; wide hero text becomes (88px). Mobile breakpoints progressively reduce it, reaching (40px) at the narrowest layout.
- **Working titles:** workspace default uses its title role; detail headings use (26px). Candidate portal titles use their separate role, reduced to (26px) at the mobile breakpoint.
- **Account and operations:** operations headings are fluid; login overrides its heading to the account title role.
- **Body and labels:** workspace body is the working baseline; tables and most metadata use (12px). Operations paragraphs and landing body retain their own scale and line height. Source paragraph measures generally fall within (68–75ch) where specified.
- **Forms:** workspace controls use (13px) on desktop, operations controls (14px); both become (16px) at their mobile breakpoint.
- **Illustration:** landing preview metadata is smaller (9–11px), with some narrow-layout text at (8px). That scale belongs to the static fictional preview.

**The Working Text Rule.** Preserve readable working text and mobile input sizes; do not use the miniature illustration scale for product controls.

## Layout

Spacing primitives above record recurring increments, not a required universal grid.

| Surface | Desktop | Responsive behavior |
| --- | --- | --- |
| Workspace | Fixed rail (248px), topbar (72px), main inset (34px 38px 42px), flexible queue plus (265px) side column | Rail (225px) at ≤1300px; content/detail/forms collapse at ≤1080px. At ≤780px, rail becomes an expandable header menu, counts become 2×2, forms stack, candidate table becomes labeled grid rows, and visible native sorting replaces the hidden header operation. Other tables keep contained scrolling. |
| Candidate | Main max-width (800px), inset (28px), card padding (30px) | At ≤780px, inset (20px), cards (24px), stacked case/withdrawal groups and vertical step labels. |
| Landing | Container `min(1320px, calc(100% - 96px))`, section spacing (120px), two-column hero and broad fictional preview | Hero stacks at ≤900px; major sections and preview stack at ≤700px; narrow inset (16px) at ≤380px. Illustration rail hides before preview columns stack. |
| Operations/account | Operations max-width (1160px), inset (36px); generic account/legal main (760px); login (440px) | Metrics become two columns at ≤800px. Setup/form groups stack and inputs enlarge at ≤560px. Login becomes top-aligned. |

Scoped breakpoints are recorded in [.impeccable/design.json](.impeccable/design.json). Workspace search, status and sort choices persist in its hash URL and restore on reload.

## Elevation & Depth

The system is mostly flat: white surfaces, pale tints, thin borders and a dark rail provide grouping. Regular panels and marketing previews have no shadow. The workspace toast has the only box shadow in these three stylesheets (`0 8px 28px #20272324`), lifting temporary feedback above the task.

**The Quiet Depth Rule.** Use borders and tonal grouping for ordinary content; keep toast elevation tied to temporary feedback.

Motion supplies immediate state and press feedback. Workspace transitions use (150ms ease); landing controls (160ms ease-out) and its headline settles once over (600ms). Operations uses a one-pixel press translation. Reduced-motion rules differ by surface; operations retains its press translation. Only landing supplies a `prefers-contrast: more` override. There is no translucent material or reduced-transparency rule in these sources.

## Shapes

Workspace panels and candidate cards use the panel radius; workspace controls use the eight-pixel control shape; operations controls use seven pixels. Landing preview containers use twelve pixels and its controls use eight. Working badges use five-pixel corners, while illustration badges use four. Initial avatars and small step markers identify people/stages without stock portraits. Open rows and dividers balance enclosed groups.

## Components

### Buttons

Primary actions use the surface's forest and white text. Secondary actions use restrained borders; workspace destructive actions use danger text and a warm hover fill. Focus uses a three-pixel outline with visible offset. Buttons provide immediate press response and disabled/busy feedback. Default workspace/operations buttons have minimum height (44px), landing defaults (52px); workspace small buttons (38px) and operations secondary controls (42px) are source exceptions.

### Status labels

Working badges include text and a decorative colored dot. Distinguish “Awaiting approval,” “Not started,” “In progress,” “Needs review,” “Review complete,” “Withdrawn,” “Manually reviewed” and “Provider verified.” Candidate review readiness says “Ready for review.” Status and access labels sit beside/after headings or in explanatory content. Completion is not a hiring approval or provider attestation.

### Cards, fields and states

Bordered white containers group related evidence, consent and forms. Tinted notices explain next steps and setup. Use labeled native inputs, selects, textareas and checkboxes, visible hover/focus, inline help and invalid feedback. Search receives a containing focus outline. Loading, saves and counts announce status; errors include recovery actions; blank and filtered-empty queues have distinct actions. Correction and withdrawal remain visible in the candidate journey.

### Navigation and queue

The rail exposes active-route state with `aria-current`. Its mobile menu exposes `aria-expanded`, Escape closure and focus return. Desktop name sorting updates `aria-sort`; mobile uses a visible select with newest-first and both name orders. Export appears only for authorized roles. The landing preview is labeled fictional semantic HTML with static illustration controls.

### Provider handoff

Identity actions reflect provider configuration and existing hosted sessions. Unconfigured states explain activation; an existing hosted URL can be resumed. Human source review remains visibly separate from provider identity results. Free workspace access does not imply live provider activation.

## Do's and Don'ts

### Do:

- **Do** use each surface's source tokens and preserve the final dark-rail overrides.
- **Do** use Manrope, visible keyboard focus, labeled native controls and implemented mobile input sizes.
- **Do** combine status color with text and distinguish human review from provider results.
- **Do** provide useful loading, first-run, filtered-empty, save and error states.
- **Do** label illustrative records as fictional and use tenant API data for working counts.

### Don't:

- **Don't** restore superseded blue-gray tokens, serif marketing type or paid-pilot access messaging as the current system.
- **Don't** promote illustration text sizes, static controls or sample records to working product defaults.
- **Don't** invent provider coverage, certificates, customer proof, suitability scores or performance metrics.
- **Don't** hide approval, correction, withdrawal or staff authentication to simplify a screen.
- **Don't** claim universal breakpoints, radii, control heights, contrast or motion behavior.
