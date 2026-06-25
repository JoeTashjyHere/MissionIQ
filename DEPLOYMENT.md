# MissionIQ — Offline / Restricted-Network Deployment (Work Laptop)

These images were built on an unrestricted network so they already contain every
Python and Node dependency that the corporate firewall blocks (`asyncpg`,
`pgvector`, `tiktoken`, `python-docx`, etc.). On the work laptop you only need
Docker, this repository, and a way to fetch the images — **no PyPI or npm access
required, and you never run `docker build`.**

> **Platform: `linux/amd64`.** The published images are built for `linux/amd64`,
> which is what Windows + Docker Desktop on Intel/AMD hardware needs. (An earlier
> ARM build existed; it has been replaced — if you pulled before 2026-06-25,
> re-pull to get the amd64 version.)

## Images

| Component | Image reference | Platform |
|-----------|-----------------|----------|
| Backend (FastAPI + Python 3.12) | `missioniq-backend:latest` | linux/amd64 |
| Frontend (Next.js 15 + React 19) | `missioniq-frontend:latest` | linux/amd64 |
| Database (Postgres 16 + pgvector) | `pgvector/pgvector:pg16` | linux/amd64 |

`docker-compose.local.yml` expects the local names `missioniq-backend:latest` and
`missioniq-frontend:latest`, so after pulling from a registry you must re-tag
(commands below).

Choose ONE of the transfer options. **Option A (Docker Hub) is confirmed working
on the corporate network and is recommended.**

---

## Option A — Pull from Docker Hub (recommended)

Private repo `missioniq/missioniq`, with the two images stored as tags
`:backend` and `:frontend`.

```powershell
docker login -u missioniq        # enter your Docker Hub password or access token

docker pull missioniq/missioniq:backend
docker pull missioniq/missioniq:frontend
docker pull pgvector/pgvector:pg16

# Re-tag to the names docker-compose.local.yml expects:
docker tag missioniq/missioniq:backend  missioniq-backend:latest
docker tag missioniq/missioniq:frontend missioniq-frontend:latest

cd C:\Users\d-joseph.tashjy\MissionIQ\MissionIQ
git pull
docker compose -f docker-compose.local.yml up
```

---

## Option B — Pull from GitHub Container Registry (GHCR)

Private packages under your GitHub account. Requires a classic Personal Access
Token with the **`read:packages`** scope (create at
GitHub → Settings → Developer settings → Personal access tokens (classic)).

```powershell
docker login ghcr.io -u JoeTashjyHere   # paste the read:packages PAT as the password

docker pull ghcr.io/joetashjyhere/missioniq-backend:latest
docker pull ghcr.io/joetashjyhere/missioniq-frontend:latest
docker pull pgvector/pgvector:pg16

docker tag ghcr.io/joetashjyhere/missioniq-backend:latest  missioniq-backend:latest
docker tag ghcr.io/joetashjyhere/missioniq-frontend:latest missioniq-frontend:latest

cd C:\Users\d-joseph.tashjy\MissionIQ\MissionIQ
git pull
docker compose -f docker-compose.local.yml up
```

---

## Option C — Download the image archive from a GitHub Release

A single `linux/amd64` archive (~930 MB) is attached to the
[`v0.1.0-images`](https://github.com/JoeTashjyHere/MissionIQ/releases/tag/v0.1.0-images)
release. Use this if both registries are blocked. (The repo is currently public,
so this download needs no authentication.)

```powershell
cd C:\Users\d-joseph.tashjy\

# Download (either command works):
gh release download v0.1.0-images --repo JoeTashjyHere/MissionIQ --pattern "missioniq-images-amd64.tar.gz"
# or, without the gh CLI:
curl.exe -L -o missioniq-images-amd64.tar.gz https://github.com/JoeTashjyHere/MissionIQ/releases/download/v0.1.0-images/missioniq-images-amd64.tar.gz

# Load all three images (gzip auto-detected). docker load restores the
# missioniq-backend:latest / missioniq-frontend:latest / pgvector tags directly:
docker load -i missioniq-images-amd64.tar.gz

cd C:\Users\d-joseph.tashjy\MissionIQ\MissionIQ
git pull
docker compose -f docker-compose.local.yml up
```

---

## Option D — USB transfer (only if a drive is permitted)

If you can use an approved USB drive, copy `missioniq-images-amd64.tar.gz` onto it
from the build laptop, then on the work laptop:

```powershell
docker load -i E:\missioniq-images-amd64.tar.gz
cd C:\Users\d-joseph.tashjy\MissionIQ\MissionIQ
git pull
docker compose -f docker-compose.local.yml up
```

> Make sure the archive is the `*-amd64` one. An older `missioniq-images.tar.gz`
> built on Apple Silicon is `linux/arm64` and will NOT run on this laptop.

---

## Verify the architecture (quick sanity check)

After loading/pulling, confirm you have amd64 images:

```powershell
docker image inspect missioniq-backend:latest  --format "{{.Os}}/{{.Architecture}}"
docker image inspect missioniq-frontend:latest --format "{{.Os}}/{{.Architecture}}"
# Both should print: linux/amd64
```

---

## Accessing MissionIQ

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |

**Demo login (Apex Federal showcase, seeded automatically on first boot):**

```
Email:    sarah.mitchell@apexfederal.demo
Password: MissionIQ!Demo2026
```

Other seeded users share the same password: `michael.reynolds@`, `jennifer.carter@`,
`david.kim@`, `emily.turner@` (all `@apexfederal.demo`).

> The generic `demo@missioniq.dev` user is only created by the non-Apex seed
> (`python -m seeds.seed`). `docker-compose.local.yml` runs the Apex seed.

---

## How `docker-compose.local.yml` differs from `docker-compose.yml`

- Uses `image:` (pre-built) instead of `build:` — nothing compiles at work.
- Does **not** publish the Postgres port, to avoid clashing with any Postgres
  already running on `localhost:5433`. The backend still reaches it internally.
- Application code is still bind-mounted from the repo, so `git pull` updates
  the app with no rebuild. Only dependencies live in the images.

---

## AWS Bedrock (optional)

The default `.env` uses `local_stub`, so MissionIQ runs without any cloud LLM.
To use Bedrock (e.g. GovCloud):

1. In `.env`, put `bedrock` first in `MIQ_LLM_PROVIDER_ORDER` and set
   `AWS_BEDROCK_REGION=us-gov-west-1` (plus the model IDs your account allows).
2. Provide credentials by setting `AWS_PROFILE` / `AWS_REGION` and uncommenting
   the `~/.aws` volume mount in `docker-compose.local.yml`. On Windows set
   `AWS_CONFIG_DIR=%USERPROFILE%\.aws` first.

---

## Troubleshooting

**`no matching manifest for linux/amd64` / image won't start**
You have an ARM image. Re-pull from a registry (Options A/B) or load the
`*-amd64` archive (Option C). Verify with the architecture check above.

**`.env` missing / backend exits on `MIQ_JWT_SECRET`**
```powershell
Copy-Item .env.example .env   # then confirm MIQ_JWT_SECRET is non-empty
```

**Images not found when starting**
```powershell
docker images | findstr missioniq
# Ensure the re-tag step ran: missioniq-backend:latest and missioniq-frontend:latest must exist.
```

**Port already in use (3000 / 8000)**
Stop whatever is using the port, or edit the published ports in
`docker-compose.local.yml`.

**Reset everything (wipes the seeded demo DB)**
```powershell
docker compose -f docker-compose.local.yml down -v
docker compose -f docker-compose.local.yml up
```

**Watch logs**
```powershell
docker compose -f docker-compose.local.yml logs -f
```
