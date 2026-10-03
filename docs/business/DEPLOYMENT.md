# Hosted Vetra pilot

Frontend: https://vetra-hr.vercel.app
Staff workspace: https://vetra-hr.vercel.app/app
Backend health: https://vetra-api-production-0262.up.railway.app/healthz

Vercel project: `vetra-hr`, Jaime Henriques' projects.
Railway project: `vetra`; production service: `vetra-api`.
Both follow this repository's `main` branch.

Vercel builds static marketing and assets with `npm run build`; `vercel.json` proxies authenticated pages and APIs to Railway. Browser requests stay on the frontend origin, preserving secure session cookies and CSRF protection.

Railway uses `Dockerfile.vetra`, one Gunicorn worker, four threads, one replica in `europe-west4`, and a persistent 1GB volume mounted at `/data`. `/healthz` checks database connectivity. The entrypoint prepares volume ownership and drops privileges before starting the server.

Demo mode is disabled. Owner email is `jaimedhenriques@gmail.com`. Retrieve the generated initial password from Railway service Variables → `VETRA_ADMIN_PASSWORD`. Secrets are stored in Railway variables and are never committed. Keep `VETRA_SECRET_KEY` stable across redeployments. Changing the bootstrap password variable does not reset an existing user's password; use an authenticated administrative recovery process.

No live identity provider credentials, transactional invitation email, billing, custom domain, SSO, managed backups, or production screening contracts are enabled. Invitation links can be copied from the workspace. This deployment remains a controlled pilot; configure those services and complete legal/security readiness work before onboarding paying customers or scaling. SQLite requires one replica; migrate to managed PostgreSQL before horizontal scaling. Enable and test volume backups before collecting real candidate data.
