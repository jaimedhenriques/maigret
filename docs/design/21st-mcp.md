# 21st.dev account and component workflow

Installed `@21st-dev/cli@1.18.0` globally. Reproduce with `npm i -g @21st-dev/cli@1.18.0` (review npm lifecycle scripts before enabling them). The supplied API key authenticated the account; `21st usage` reports the existing paid tier. No interactive browser login is required when using API-key authentication. NODE_USE_ENV_PROXY=1 is needed for Node fetch in this execution environment.

The streamable HTTP MCP endpoint `https://21st.dev/api/mcp` was initialized and tools/list verified `search`, `get_component`, `get_inspiration`, and other tools. The local ignored `.mcp.json` is configured with the supplied key and permission 0600. `.mcp.json.example` is a shareable template; clients with environment substitution can resolve API_KEY_21ST. A host MCP client may need a restart to load configuration; this session also uses an authenticated raw MCP client through `scripts/21st-client.py`.

Secrets are stored outside this repository in user-local secret storage, never in source, diagrams, screenshots or deployed browser code. In CI set API_KEY_21ST as a protected secret. The runner reads the environment first, then the local private credential file; outputs redact the key. Rotate the key in 21st's account settings if replacing the shared credential.

Commands:

- `npm run design:21st -- tools` verifies MCP tools.
- `npm run design:21st -- search sidebar data table` searches the authenticated catalog.
- `npm run design:21st -- component 25151` retrieves a selected component; inspect quota/licensing and runtime compatibility first.
- `npm run design:21st -- cli usage --json` checks account state.
- `npm run design:21st -- cli search "sidebar navigation" --type c --limit 3 --json` uses the CLI.
- `npm run design:21st -- cli review vetra/templates/landing.html vetra/templates/workspace.html --json` runs deterministic local rules where supported.

Source review for this redesign: Team Members Data Table, demo ID25151, author olewandowski1, retrieved through the authenticated account and kept in ignored .design-toolchain/21st/. Inspected search/filter/empty-row and keyboard-readable table patterns. No sales scoring, fake live streams, unbacked bulk actions or third-party candidate data is adopted. The current product is Flask/Jinja/vanilla JS; React/TanStack source is reference material, not a falsely advertised installed React runtime. Native primitives adapt official MIT shadcn Button/Input/Badge/Table/Sidebar patterns to the application, with actual provenance recorded in tooling.md.
