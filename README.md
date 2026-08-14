# Ledger

A magazine-style **Django blog** with a public site and a versioned JSON API.

- Draft / published / archived workflow and scheduled `published_at`
- Categories, tags, markdown, reading time, view counts
- Nested comments, likes, bookmarks
- Author studio (write, edit, saved posts)
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

Open http://127.0.0.1:8000

Demo login: **hgus** / **ledger12345**

Admin: `python manage.py createsuperuser` then http://127.0.0.1:8000/admin/

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
