# Bluewave Academy — Production Deployment Guide

## Stack

| Layer | Service |
|---|---|
| App hosting | Railway |
| Database | Railway PostgreSQL plugin |
| Cache + WebSockets | Railway Redis plugin |
| File storage | Supabase Storage (S3-compatible) |
| Static files | WhiteNoise (served directly from Gunicorn) |
| ASGI server | Gunicorn + UvicornWorker (supports Django Channels) |

---

## 1. Supabase — Storage Setup

1. Create a new Supabase project at https://supabase.com
2. Go to **Storage** and create two buckets:
   - `media` — profile pics, blog images, tutorial files, classroom materials, PDF submissions
   - `papers` — SpecialPaper PDFs (private, accessed via signed URLs)
3. Set `media` bucket policy to **private** (signed URLs used for authenticated downloads; public blog images use the public URL path)
4. Set `papers` bucket policy to **private**
5. Go to **Project Settings → Storage → S3 Connection** and copy:
   - Endpoint URL → `SUPABASE_S3_ENDPOINT`
   - Region → `SUPABASE_S3_REGION`
   - Access Key ID → `SUPABASE_S3_ACCESS_KEY`
   - Secret Access Key → `SUPABASE_S3_SECRET_KEY`
6. Go to **Project Settings → API** and copy:
   - Project URL → `SUPABASE_URL`
   - `anon` key → `SUPABASE_ANON_KEY`
   - `service_role` key → `SUPABASE_SERVICE_KEY`

---

## 2. Railway — Project Setup

1. Create a new Railway project
2. Add your GitHub repo as the source
3. Add a **PostgreSQL** plugin — Railway auto-injects `DATABASE_URL`
4. Add a **Redis** plugin — Railway auto-injects `REDIS_URL`
5. Set all required environment variables (see section 4 below)
6. Railway will build using `nixpacks.toml` and start via `Procfile`

---

## 3. Environment Variables to Set on Railway

Copy these into Railway → Project → Variables. Values come from your Supabase dashboard and email provider.

```
DJANGO_SECRET_KEY        # generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
DEBUG                    # False
DJANGO_ALLOWED_HOSTS     # yourapp.up.railway.app,yourdomain.com
CSRF_TRUSTED_ORIGINS     # https://yourapp.up.railway.app,https://yourdomain.com

# Supabase
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_KEY
SUPABASE_S3_ENDPOINT
SUPABASE_S3_REGION       # auto
SUPABASE_S3_ACCESS_KEY
SUPABASE_S3_SECRET_KEY
SUPABASE_MEDIA_BUCKET    # media
SUPABASE_PAPERS_BUCKET   # papers

# Email
EMAIL_HOST_USER
EMAIL_HOST_PASSWORD
DEFAULT_FROM_EMAIL

# AI
GROQ_API_KEY

# Note: DATABASE_URL and REDIS_URL are injected automatically by Railway plugins
```

---

## 4. First Deploy Checklist

- [ ] `DJANGO_SECRET_KEY` is a fresh, long random string (not the insecure dev default)
- [ ] `DEBUG=False`
- [ ] `DJANGO_ALLOWED_HOSTS` includes your Railway domain and custom domain
- [ ] `CSRF_TRUSTED_ORIGINS` includes `https://` versions of all domains
- [ ] Both Supabase buckets (`media`, `papers`) created and set to private
- [ ] All six Supabase S3 variables set in Railway
- [ ] PostgreSQL plugin added to Railway project (`DATABASE_URL` auto-set)
- [ ] Redis plugin added to Railway project (`REDIS_URL` auto-set)
- [ ] Email credentials set (or leave blank to disable outgoing mail)
- [ ] `GROQ_API_KEY` set for AI grading to work
- [ ] Custom domain added in Railway → Settings → Domains (optional)
- [ ] Custom domain added to `DJANGO_ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`

---

## 5. Migrate Existing Media Files (one-time)

If you have files in the local `media/` folder from development, upload them to Supabase Storage using the Supabase CLI or dashboard before going live:

```bash
# Install Supabase CLI
npm install -g supabase

# Upload local media folder to the media bucket
supabase storage cp --recursive ./media/ ss:///media/
```

Or upload manually via the Supabase dashboard Storage browser.

---

## 6. Local Development

Local dev continues to work with SQLite + local `media/` folder. Supabase storage is only activated when `SUPABASE_S3_ENDPOINT`, `SUPABASE_S3_ACCESS_KEY`, and `SUPABASE_S3_SECRET_KEY` are all set.

```bash
# Install dependencies
uv sync

# Run locally
python manage.py runserver
```

---

## 7. Scaling Notes

- **Workers**: The `Procfile` starts 2 Gunicorn workers with 4 threads each. Adjust `--workers` based on Railway instance RAM (rule of thumb: `2 * CPU + 1`).
- **File uploads**: Max memory buffer is 50 MB. Files larger than 50 MB stream to a temp file before upload to Supabase — no memory pressure on large video uploads.
- **WebSockets**: Channels uses Redis as the layer. The UvicornWorker supports both HTTP and WebSocket connections in a single process.
- **Sessions**: Stored in Redis (production) — zero database hits per request for session reads.
- **Static files**: WhiteNoise serves Brotli-compressed, content-hashed static files with long-lived `Cache-Control` headers. No CDN needed for static assets.
