# MissionIQ — Offline Deployment (Work Laptop)

These images were built on an unrestricted (home) network so they already
contain every Python and Node dependency that the corporate firewall blocks
(`asyncpg`, `pgvector`, `tiktoken`, `python-docx`, etc.). You only need Docker
and this repository on the work laptop — no PyPI or npm access required.

## What you're transferring

| Image | Tag | Size (approx) |
|-------|-----|---------------|
| Backend (FastAPI + Python 3.12) | `missioniq-backend:latest` | ~1.6 GB |
| Frontend (Next.js 15 + React 19) | `missioniq-frontend:latest` | ~2.4 GB |
| Database (Postgres 16 + pgvector) | `pgvector/pgvector:pg16` | ~0.64 GB |

All three are bundled into a single archive: **`missioniq-images.tar.gz`**
(compressed, ~1.3–1.6 GB).

---

## Option A — USB transfer (no network needed)

### On the work laptop

1. Copy `missioniq-images.tar.gz` from the USB drive, e.g. to
   `C:\Users\d-joseph.tashjy\`.

2. Load all three images into Docker (gzip is auto-detected):

   ```powershell
   docker load -i C:\Users\d-joseph.tashjy\missioniq-images.tar.gz
   ```

3. Confirm the images are present:

   ```powershell
   docker images | findstr missioniq
   docker images | findstr pgvector
   ```

   You should see `missioniq-backend:latest`, `missioniq-frontend:latest`,
   and `pgvector/pgvector:pg16`.

4. Make sure the repo is up to date (this works on the corporate network —
   only PyPI/npm are blocked, not GitHub):

   ```powershell
   cd C:\Users\d-joseph.tashjy\MissionIQ\MissionIQ
   git pull
   ```

5. Start MissionIQ using the pre-built images:

   ```powershell
   docker compose -f docker-compose.local.yml up
   ```

That's it. The backend runs DB migrations and seeds the Apex Federal demo on
first boot, then both services come up.

---

## Option B — Registry transfer (GitHub Container Registry or Docker Hub)

If USB is inconvenient, push from the build laptop and pull at work.

### On the build (home) laptop

```bash
# GitHub Container Registry (private by default). Create a classic PAT with
# the write:packages scope first.
echo <YOUR_GITHUB_TOKEN> | docker login ghcr.io -u <YOUR_GITHUB_USERNAME> --password-stdin

docker tag missioniq-backend:latest  ghcr.io/<YOUR_GITHUB_USERNAME>/missioniq-backend:latest
docker tag missioniq-frontend:latest ghcr.io/<YOUR_GITHUB_USERNAME>/missioniq-frontend:latest

docker push ghcr.io/<YOUR_GITHUB_USERNAME>/missioniq-backend:latest
docker push ghcr.io/<YOUR_GITHUB_USERNAME>/missioniq-frontend:latest
# pgvector/pgvector:pg16 is already public on Docker Hub — no push needed.
```

### On the work laptop

```powershell
echo <YOUR_GITHUB_TOKEN> | docker login ghcr.io -u <YOUR_GITHUB_USERNAME> --password-stdin

docker pull ghcr.io/<YOUR_GITHUB_USERNAME>/missioniq-backend:latest
docker pull ghcr.io/<YOUR_GITHUB_USERNAME>/missioniq-frontend:latest
docker pull pgvector/pgvector:pg16

# Re-tag to the names docker-compose.local.yml expects:
docker tag ghcr.io/<YOUR_GITHUB_USERNAME>/missioniq-backend:latest  missioniq-backend:latest
docker tag ghcr.io/<YOUR_GITHUB_USERNAME>/missioniq-frontend:latest missioniq-frontend:latest

cd C:\Users\d-joseph.tashjy\MissionIQ\MissionIQ
git pull
docker compose -f docker-compose.local.yml up
```

> Docker Hub works the same way — substitute `<DOCKERHUB_USERNAME>/...` for the
> `ghcr.io/...` references and `docker login` with no registry argument.

---

## Accessing MissionIQ

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |

**Demo login (Apex Federal showcase, seeded automatically):**

```
Email:    sarah.mitchell@apexfederal.demo
Password: MissionIQ!Demo2026
```

Other seeded users share the same password: `michael.reynolds@`, `jennifer.carter@`,
`david.kim@`, `emily.turner@` (all `@apexfederal.demo`).

> The generic `demo@missioniq.dev` user is only created by the non-Apex seed
> (`python -m seeds.seed`). `docker-compose.local.yml` runs the Apex seed.

---

## How this differs from `docker-compose.yml`

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

**Images not found when starting**
```powershell
docker images | findstr missioniq
# Re-load from the archive or re-tag from the registry (see above).
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
