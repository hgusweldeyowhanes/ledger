# Ledger

A magazine-style blog with a public site, versioned JSON API, and React SPA.

- Draft / published / archived workflow and scheduled `published_at`
- Categories, tags, markdown, reading time, view counts
- Nested comments with **author moderation** (non-author comments start pending)
- Likes, bookmarks, **follow authors** + following feed
- **Post series** (ordered multi-part essays)
- **In-app notifications** (likes, comments, follows, approvals)
- **Newsletter** subscribe/confirm/unsubscribe + digest command
- **Dark / light theme** toggle (saved in `localStorage`)
- **Social share** (OG tags, copy link, X, LinkedIn)
- Author studio (write, edit, saved posts, moderation, series)
- JWT + token registration, pagination, search, filters
- RSS feed and sitemap
- Soft-delete instead of hard-deleting posts

## Run

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_blog
python manage.py runserver
```

## React SPA

```bash
cd frontend
npm install
npm run dev
```

http://127.0.0.1:5173 (proxies `/api` to Django).

### Cover upload, replies, newsletter

- Write form supports cover image upload (multipart to the API).
- Post comments support one-level nested replies.
- Newsletter confirm/unsubscribe links open the React routes `/newsletter/confirm/:token` and `/newsletter/unsubscribe/:token`.

### Real email (SMTP)

Copy `.env.example` → `.env` and set:

```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=Ledger <you@domain.com>
FRONTEND_URL=http://127.0.0.1:5173
```

If `EMAIL_HOST` is empty, mail prints to the console (dev).

### Production (React hosted by Django)

```bash
cd frontend && npm ci && npm run build && cd ..
pip install -r requirements.txt
set SERVE_SPA=true
set DJANGO_DEBUG=false
set FRONTEND_URL=https://your-domain.example
set SITE_URL=https://your-domain.example
python manage.py collectstatic --noinput
python manage.py migrate
gunicorn myproject.wsgi:application --bind 0.0.0.0:8000
```

Or Docker / Render: `Dockerfile` + `render.yaml` (set `DJANGO_ALLOWED_HOSTS`, `SITE_URL`, `FRONTEND_URL`, and SMTP vars in the dashboard).

Demo login: **hgus** / **ledger12345** (also **reader** / **ledger12345**)

Admin: `python manage.py createsuperuser` then http://127.0.0.1:8000/admin/

### Newsletter digest

Uses the console email backend by default (messages print in the terminal).

```bash
python manage.py send_newsletter_digest
python manage.py send_newsletter_digest --since 48
```

For real SMTP, set `EMAIL_BACKEND`, `EMAIL_HOST`, and `DEFAULT_FROM_EMAIL` in the environment / settings.

## Site routes

| Path | Notes |
|---|---|
| `/` | Home |
| `/following/` | Posts from authors you follow (auth) |
| `/series/` | Series index |
| `/series/<slug>/` | Series detail |
| `/notifications/` | In-app notifications (auth) |
| `/dashboard/` | Studio + moderation queue |
| `/newsletter/subscribe/` | POST email |
| `/newsletter/confirm/<token>/` | Confirm subscription |
| `/newsletter/unsubscribe/<token>/` | Unsubscribe |

## API

| Method | Path | Notes |
|---|---|---|
| POST | `/api/register/` | username, email, password, password2 |
| POST | `/api/token/` | JWT obtain |
| POST | `/api/token/refresh/` | JWT refresh |
| GET | `/api/me/` | current user |
| GET | `/api/posts/` | published list (search, filter, order) |
| POST | `/api/posts/` | create (auth) |
| GET | `/api/posts/{slug}/` | detail + related |
| POST | `/api/posts/{slug}/publish/` | author |
| POST | `/api/posts/{slug}/like/` | toggle |
| POST | `/api/posts/{slug}/bookmark/` | toggle |
| GET | `/api/posts/mine/` | your drafts + published |
| GET | `/api/feed/following/` | following feed (auth) |
| POST | `/api/authors/{username}/follow/` | toggle follow |
| GET/POST | `/api/series/` | list / create series |
| GET | `/api/notifications/` | in-app notifications |
| POST | `/api/notifications/mark_read/` | mark all read |
| POST | `/api/newsletter/subscribe/` | `{ "email": "..." }` |
| POST | `/api/comments/{id}/approve/` | post author |
| POST | `/api/comments/{id}/reject/` | post author |
| GET | `/api/feed/` | RSS |
| GET | `/sitemap.xml` | sitemap |

Example:

```bash
curl http://127.0.0.1:8000/api/posts/
```

## Tests

```bash
python manage.py test blog
```
