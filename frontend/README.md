# Ledger frontend

Vite + React SPA for the Ledger API.

## Local (dev)

Terminal 1 — API:

```bash
cd ..
.venv\Scripts\activate
python manage.py runserver
```

Terminal 2 — React:

```bash
npm install
npm run dev
```

Open http://127.0.0.1:5173

## Features

- Cover image upload on Write
- Nested comment replies (one level)
- Newsletter confirm / unsubscribe pages
- JWT auth, studio, series, following, notifications, theme

## Production build (served by Django)

```bash
npm ci
npm run build
```

Then on the Django host set `SERVE_SPA=true` and `DJANGO_DEBUG=false`. See root README / `Dockerfile` / `render.yaml`.
