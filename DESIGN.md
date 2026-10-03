# Vetra interface

The workspace is an operate surface: the candidate queue is the primary artifact. The first viewport shows live counts from the tenant's data, pending work, a searchable candidate table, and recent events. The signature interaction follows a candidate from invitation through approval and review, with a visible distinction between manual evidence review and provider-verified identity.

Tokens are defined in vetra/static/workspace.css: paper #f6f7f9, white #ffffff, ink #172b3a, muted #63717d, line #e5e9ec, teal #147d6b, teal dark #0f6153, mint #e8f5ef, amber #946217. Manrope is self-hosted under its SIL Open Font License; the marketing page adds Georgia for editorial headings. Body 14px, secondary table information 10–12px, primary title 30px. Panel radius 14px, controls 7–8px. One-pixel borders define surface elevation.

The desktop rail is 240px; below 760px navigation becomes a horizontal row. Secondary panels move under the table by 1050px. Tables retain their readable column sizes in a contained horizontal scroll area. Candidate forms are stacked on mobile. Color statuses always include text; buttons have visible keyboard focus; async errors name a recovery action. All records, counts, and states in the demo are explicitly fictional.
