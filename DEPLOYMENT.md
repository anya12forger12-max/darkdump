# Deployment

Darkdump ships one multi-stage `Dockerfile` with two independent targets:

| Target | What it runs | Base image | User |
|--------|--------------|------------|------|
| `cli`  | `python darkdump.py` | `python:3.13-slim` | non-root `app` |
| `web`  | `python darkdump-web/app.py` (Flask UI) | `python:3.13-slim` | non-root `app` |

Both targets install the pinned CLI dependencies from `requirements.txt`. Only
the `web` target additionally installs Flask. No secrets are baked into either
image.

## Prerequisites

- Docker Engine with Compose v2 (`docker compose`).
- Network access to PyPI at image build time.
- Optional: a reachable Tor SOCKS proxy only if you use `-p` in the CLI or the
  Tor toggle in the web UI. Configure that externally; never commit proxy
  credentials.

## CLI usage

Build the CLI image:

```bash
docker build --target cli -t darkdump-cli:local .
```

The image `CMD` is `python darkdump.py`, so flags go after the image name:

```bash
# Basic search
docker run --rm darkdump-cli:local -q "privacy tools" -a 10

# See all options
docker run --rm darkdump-cli:local --help

# Save results to a file on the host (host ./out must exist and be writable)
mkdir -p out
docker run --rm -v "$PWD/out:/app/out" darkdump-cli:local \
  -q "security research" -a 20 -o /app/out/results.json
```

For proxy-based engines (`-p`), attach a Tor proxy container/network or point
the CLI's proxy configuration at one you control. Do not pass secrets via
image build arguments or environment files in this repository.

## Web deployment

From the repository root:

```bash
cp .env.example .env          # optional local overrides; safe placeholder values
docker compose up -d --build
```

Then open <http://127.0.0.1:50001>. To stop: `docker compose down` (add `-v`
only if you intentionally want to delete the `darkdump-data` volume).

`docker-compose.yml` builds the `web` target, publishes host port `50001` to
container port `50001`, sets `DARKDUMP_HOST=0.0.0.0` so Flask listens on all
container interfaces, uses `restart: unless-stopped`, and mounts the named
volume `darkdump-data` at `/app/data` (reserved for user outputs; the current
UI streams exports back to the browser instead of writing files).

The image can also be run directly:

```bash
docker build --target web -t darkdump-web:local .
docker run --rm -p 50001:50001 -e DARKDUMP_HOST=0.0.0.0 darkdump-web:local
```

## Ports

| Port | Direction | Purpose |
|------|-----------|---------|
| `50001` | host → container TCP | Flask web UI (HTTP) |

If you change `DARKDUMP_PORT`, update the port mapping in `docker-compose.yml`
(`"50001:50001"`) at the same time. The web UI has no built-in authentication
or TLS: keep it on a trusted/local network, or put it behind an authenticating
reverse proxy before exposing it.

## Environment variables

| Variable | Default (local `app.py`) | Container / compose value | Purpose |
|----------|--------------------------|---------------------------|---------|
| `DARKDUMP_HOST` | `127.0.0.1` | `0.0.0.0` | Address Flask binds to. Local default is unchanged; containers must bind all interfaces to publish the port. |
| `DARKDUMP_PORT` | `50001` | `50001` | Port Flask listens on. Also used by the health check. |
| `DARKDUMP_WEB_IMAGE` | `darkdump-web:local` | `darkdump-web:local` | Image tag used by Compose; override with a pinned GHCR tag for deployments. |

Compose reads `.env` automatically for `DARKDUMP_WEB_IMAGE`; `DARKDUMP_HOST`
and `DARKDUMP_PORT` are pinned in `docker-compose.yml` to `0.0.0.0:50001` by
design. The same variables in `.env.example` apply to direct `app.py` runs and
`docker run -e ...`. Non-container behavior is unchanged when they are unset.

## Health checks

The `web` image has a `HEALTHCHECK` that fetches `http://127.0.0.1:50001/`
with Python's `urllib` (no `curl` in slim images), using `$DARKDUMP_PORT` if
set. Compose declares the same check.

```bash
docker inspect --format '{{.State.Health.Status}}' darkdump-web
docker compose ps                 # shows health status of the web service
docker logs darkdump-web          # diagnostics if status is "unhealthy"
```

Common causes of an unhealthy container: host port `50001` already in use, a
`DARKDUMP_PORT` value that does not match the published port, or a failed
dependency install.

## CI / published images

`.github/workflows/docker.yml` builds both targets on pull requests to `main`
and on pushes to `main`. PR builds do not log in or push. Main-branch builds
push to GHCR with `GITHUB_TOKEN`:

```
ghcr.io/<OWNER>/<REPO>:cli-<commit-sha>    ghcr.io/<OWNER>/<REPO>:cli-latest
ghcr.io/<OWNER>/<REPO>:web-<commit-sha>    ghcr.io/<OWNER>/<REPO>:web-latest
```

The workflow requests `contents: read` and `packages: write`. The GHCR package
must be connected to the repository (or the token must have package write
access) for the push to succeed.

## Upgrade

Prefer immutable, commit-SHA-pinned tags for production:

```bash
# Build locally from a specific revision
git fetch --tags
git checkout <version-tag>
docker compose up -d --build
docker inspect --format '{{.State.Health.Status}}' darkdump-web

# Or deploy a published image without rebuilding (pin the SHA tag)
DARKDUMP_WEB_IMAGE=ghcr.io/<OWNER>/<REPO>:web-<commit-sha> docker compose pull
DARKDUMP_WEB_IMAGE=ghcr.io/<OWNER>/<REPO>:web-<commit-sha> docker compose up -d
```

Always confirm the health check reports `healthy` before routing traffic to
the new container.

## Rollback

With local builds, check out the previous revision and rebuild:

```bash
git checkout <previous-version-tag>
docker compose up -d --build
```

With published images, point the deployment at the previous immutable SHA tag
and restart:

```bash
DARKDUMP_WEB_IMAGE=ghcr.io/<OWNER>/<REPO>:web-<previous-commit-sha> \
  docker compose up -d --force-recreate
```

The named `darkdump-data` volume survives container replacement; do not use
`docker compose down -v` during a rollback unless deleting stored outputs is
intentional.
