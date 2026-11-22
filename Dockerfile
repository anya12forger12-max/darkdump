# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Darkdump container images.
#
# Two build targets:
#   cli  -> python darkdump.py   (pass CLI flags after the image name)
#   web  -> Flask web UI on port 50001
#
# Both targets run as the unprivileged "app" user.
# ---------------------------------------------------------------------------

FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# CLI dependencies (pinned in requirements.txt). Flask is added only by the
# web target below; the CLI image stays free of web-server dependencies.
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY darkdump.py ./
COPY banner ./banner
COPY headers ./headers

RUN groupadd --system app \
    && useradd --system --gid app --create-home --home-dir /home/app app \
    && mkdir -p /app/data \
    && chown app:app /app/data

# ---------------------------------------------------------------------------
# Target: cli
# ---------------------------------------------------------------------------
FROM base AS cli

USER app

CMD ["python", "darkdump.py"]

# ---------------------------------------------------------------------------
# Target: web
# ---------------------------------------------------------------------------
FROM base AS web

RUN python -m pip install --no-cache-dir 'Flask>=3.0,<4'

COPY darkdump-web ./darkdump-web

ENV DARKDUMP_HOST=127.0.0.1 \
    DARKDUMP_PORT=50001

EXPOSE 50001

# Use Python's urllib instead of curl (not installed in slim images).
# The check runs inside the container; 127.0.0.1 works whether Flask is
# bound to 127.0.0.1 (local default) or 0.0.0.0 (container default).
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c 'import os, sys, urllib.request; url = "http://127.0.0.1:" + os.environ.get("DARKDUMP_PORT", "50001") + "/"; sys.exit(0 if urllib.request.urlopen(url, timeout=3).status == 200 else 1)'

USER app

CMD ["python", "darkdump-web/app.py"]
