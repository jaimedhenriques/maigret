import { mkdir, readFile, writeFile, cp } from 'node:fs/promises';
await mkdir('frontend/dist', { recursive: true });
let html = await readFile('vetra/templates/landing.html', 'utf8');
html = html.replace(/\{\{ url_for\('static', filename='landing.css'\) \}\}/g, '/static/landing.css').replaceAll('href="/"', 'href="/app"').replace('Explore a demo case', 'Open your workspace').replace('No real candidate data needed to explore.', 'Staff sign-in required. Candidate participation is by invitation.');
await writeFile('frontend/dist/index.html', html);
await cp('vetra/static', 'frontend/dist/static', { recursive: true });
