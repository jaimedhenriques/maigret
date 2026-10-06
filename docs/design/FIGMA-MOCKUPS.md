# Verisento editable Figma mockups

Created with Figma MCP on 2026-10-06. These are editable design specifications for the current redesign, with fictional sample information. They are not evidence that live provider services are activated.

[Open Verisento — product design](https://www.figma.com/design/UP9mvw7EP1aBhyypx3bXrr)

| View | Figma node | Canvas size | Editable descendants | Text layers | Component instances |
| --- | --- | --- | ---: | ---: | ---: |
| [HR overview](https://www.figma.com/design/UP9mvw7EP1aBhyypx3bXrr?node-id=2-52) | `2:52` | 1440 × 1120 | 108 | 54 | 17 |
| [Candidate approval](https://www.figma.com/design/UP9mvw7EP1aBhyypx3bXrr?node-id=2-53) | `2:53` | 390 × 1089 | 44 | 20 | 3 |
| [Marketing hero and workflow](https://www.figma.com/design/UP9mvw7EP1aBhyypx3bXrr?node-id=2-54) | `2:54` | 1440 × 1220 | 72 | 37 | 7 |
| [Component states](https://www.figma.com/design/UP9mvw7EP1aBhyypx3bXrr?node-id=2-55) | `2:55` | 1040 × 972 | 69 | 35 | 19 |

## Direction

- Warm white `#F7F8F6`, graphite `#182723`, and forest `#174D3B`.
- Manrope for headings, body text, labels, and metrics; nine shared text styles.
- Related content uses auto layout. Main cards use 12px radii; buttons and inputs use 8px radii.
- Clear status language distinguishes awaiting approval, manual review, and provider activation.
- Candidate participation is explicit. Withdrawal, correction, privacy, and provider handoff remain visible concepts.
- Free workspace access is communicated without implying free third-party verification.

## Reusable components and tokens

The file includes local Button (eight variants), Badge (three statuses), NavItem (two states), Input (three states), Checkbox (two states), MetricCard, CandidateRow, and Brand components. The state showcase contains component instances rather than detached copies.

There are 38 variables across three collections: 13 primitives, 14 semantic color aliases, and 11 spacing/radius values. Every variable has web code syntax. Semantic scopes are explicit; primitive variables are deliberately hidden. No variable uses `ALL_SCOPES`; no aliases are broken.

Discovery was completed before creation: no Code Connect mappings or existing screens were present. The subscribed Simple Design System was searched for relevant components, variables, and styles. Its Button/Input/Checkbox assets were inspected, but their remote ownership, Inter typography, and token semantics did not match Verisento’s Manrope and forest direction. Local source-specific components were therefore created instead of detaching remote assets.

## Validation

All four review frames were inspected visually. Desktop bottom clipping, action-panel spacing, and primary-button focus distinction were repaired and rechecked. All 146 text layers in the review frames assert Manrope; all 46 instances remain linked to components. The views contain 293 editable descendants and **zero image fills**. Text, vectors, inputs, rows, badges, and hierarchy remain editable. No flattened screenshots were inserted into the Figma deliverable.

Local PNGs are exported reference images only:

- [HR overview](mockups/hr-overview.png)
- [Candidate approval](mockups/candidate-approval.png)
- [Marketing hero](mockups/marketing-hero.png)
- [Component states](mockups/component-system.png)

Screenshots were retrieved using inline MCP image output after the server-provided download URLs returned HTTP 403. This did not affect design editability.

Mockups specify presentation and intended states. Existing authenticated APIs, consent checks, provider boundaries, and legal review requirements remain the implementation source of truth.
