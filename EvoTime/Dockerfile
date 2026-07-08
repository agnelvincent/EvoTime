# ─────────────────────────────────────────────────────────────────────────────
# EvoTime — Production Dockerfile
#
# Base: python:3.11-slim (small, glibc-based → required by psycopg2-binary,
#        cryptography, and Pillow's compiled C extensions).
#
# The container listens on port 8000 internally.
# docker-compose.yml maps that to HOST port 8001 to avoid conflict with
# the existing MotoReach container that already occupies host port 8000.
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# Prevent .pyc files and buffer stdout/stderr (useful for Docker logs)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# ── System dependencies ──────────────────────────────────────────────────────
# build-essential  → required to compile cryptography (Rust/CFFI-backed)
# libpq-dev        → required by psycopg2-binary at install time
# We clean apt cache in the same layer to keep the image lean.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ──────────────────────────────────────────────────────
# Copy requirements first for layer caching — only re-runs pip install
# when requirements.txt actually changes.
COPY requirements.txt /app/
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install gunicorn==21.2.0

# ── Application source ───────────────────────────────────────────────────────
COPY . /app/

# ── Static files ─────────────────────────────────────────────────────────────
# Collected at build time so Nginx (or gunicorn's whitenoise) can serve them.
# DATABASE_HOST must be resolvable at this step — it is NOT needed for
# collectstatic, but decouple reads .env. We pass a dummy DATABASE_HOST
# so the settings import doesn't fail if .env is absent inside the build context.
RUN DATABASE_HOST=localhost python manage.py collectstatic --noinput

# ── Runtime ──────────────────────────────────────────────────────────────────
EXPOSE 8000

# 3 workers is a good default for a single-core / low-traffic EC2 instance.
# Gunicorn is production-grade WSGI and handles concurrent requests correctly.
CMD ["gunicorn", "EvoTime.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120"]
