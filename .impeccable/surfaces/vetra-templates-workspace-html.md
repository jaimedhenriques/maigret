---
version: 1
slug: "vetra-templates-workspace-html"
primary_target: "vetra/templates/workspace.html"
related_targets: ["vetra/static/workspace.css","vetra/static/workspace.js"]
---

# HR workspace

Mode: Operate
Scope: `/app` overview, candidates, review, invitation, case detail, audit and settings.
Audience: authenticated HR staff with tenant-scoped owner/reviewer/viewer permissions.
Job: find the next case action, inspect evidence and resolve a documented review.
Primary actions: invite, open a case, review evidence; export only where authorized.
Proof: actual tenant API counts, audit events and check records. Demo records remain explicitly fictional.
Constraints: consent precedes review; manual source review and provider identity results stay distinct. Free access preserves staff authentication and permissions.

## Direction contract

This records the agent-selected, code-led direction of the completed redesign. No corroborated concept-seed key, ordered concept list, user-selected card or QUALITY BAR artifact exists.

THESIS: Make candidate consent, verification evidence and human review understandable in one HR workflow, organized around the queue and next action.
OWN-WORLD: Warm paper, graphite, forest and Manrope; a dark rail, flat bordered panels, restrained tinted guidance and native controls.
STORY: Invite → candidate approves/submits → source or activated provider checks → human review/corrections, with evidence provenance visible.
FIRST VIEWPORT: Navigation anchors a live queue summary, next-action region, searchable candidate table and recent activity; invitation is an immediate action.
FORM: Responsive native HTML/CSS/JavaScript with keyboard controls, loading/empty/error states and URL-persisted search/filter/sort. Mobile has equivalent visible sorting. No seed key was produced.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

Review evidence: `docs/design/FINISH-REVIEW.md`; this brief does not issue its own ship verdict.
