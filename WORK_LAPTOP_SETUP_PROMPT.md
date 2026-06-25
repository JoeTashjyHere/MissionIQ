# Work-Laptop Setup Prompt (for Claude Code)

Paste the block below into Claude Code on the Windows work laptop — or simply tell
Claude Code: "Read WORK_LAPTOP_SETUP_PROMPT.md and follow it." It brings up
MissionIQ from pre-built, public `linux/amd64` images without any build step.
See `DEPLOYMENT.md` for the human-readable version of the same procedure.

---

```text
You are an autonomous setup agent on a WINDOWS work laptop behind a locked-down
corporate network. Goal: get the MissionIQ app running using PRE-BUILT, PUBLIC
linux/amd64 Docker images. Treat DEPLOYMENT.md in the repo as the source of truth.

==================== ENVIRONMENT & HARD CONSTRAINTS ====================
- The corporate firewall BLOCKS PyPI (pip), npm, and Anaconda. Therefore you must
  NEVER run: docker build, pip install, npm install, or conda. Use ONLY the
  pre-built images referenced below.
- These work on this network: GitHub (github.com), GitHub Releases downloads, and
  Docker Hub pulls. Use them.
- Host is Windows x86_64 -> you need linux/amd64 images (the published ones are).
- Shell is PowerShell. Docker Desktop must be running.
- All artifacts below are PUBLIC, so NO docker login is required. If any pull
  returns "unauthorized"/"denied", that registry's public toggle isn't finished —
  fall back to the GitHub Release method (Step 4A), which needs no auth.
- Never print or store secrets.

==================== PROJECT FACTS ====================
- Repo path:   C:\Users\d-joseph.tashjy\MissionIQ\MissionIQ
- GitHub repo: JoeTashjyHere/MissionIQ (branch main, public)
- Compose:     docker-compose.local.yml  (runs pre-built images; bind-mounts repo
               code; does NOT publish the Postgres port)
- Runbook:     DEPLOYMENT.md (read it and follow it)
- Demo login:  sarah.mitchell@apexfederal.demo  /  MissionIQ!Demo2026
- URLs:        Frontend http://localhost:3000 | API http://localhost:8000 |
               API docs http://localhost:8000/docs

==================== IMAGE SOURCES (all public, linux/amd64) ====================
GitHub Release archive (most reliable, no auth):
  https://github.com/JoeTashjyHere/MissionIQ/releases/download/v0.1.0-images/missioniq-images-amd64.tar.gz
Docker Hub (public repo, two tags):
  missioniq/missioniq:backend
  missioniq/missioniq:frontend
GHCR:
  ghcr.io/joetashjyhere/missioniq-backend:latest
  ghcr.io/joetashjyhere/missioniq-frontend:latest
Database (public):
  pgvector/pgvector:pg16
NOTE: docker-compose.local.yml expects the LOCAL names missioniq-backend:latest
and missioniq-frontend:latest. The Release archive restores those names directly;
the registry path requires you to re-tag (Step 4B).

==================== STEPS ====================
1. PREFLIGHT: run "docker version". If the daemon isn't running, tell me to start
   Docker Desktop and STOP. Then: cd C:\Users\d-joseph.tashjy\MissionIQ\MissionIQ

2. UPDATE REPO: run "git pull". Open and read DEPLOYMENT.md so your actions match it.

3. ENV FILE: if .env does not exist, create it:
       Copy-Item .env.example .env
   Then confirm MIQ_JWT_SECRET in .env is non-empty (backend won't start otherwise).
   Leave MIQ_LLM_PROVIDER_ORDER on local_stub unless told to use Bedrock. Never commit .env.

4. GET THE IMAGES — use 4A (preferred). Use 4B only if you specifically want registries.

   4A) GitHub Release (no auth):
       cd C:\Users\d-joseph.tashjy\
       curl.exe -L -o missioniq-images-amd64.tar.gz https://github.com/JoeTashjyHere/MissionIQ/releases/download/v0.1.0-images/missioniq-images-amd64.tar.gz
       docker load -i missioniq-images-amd64.tar.gz
       (This restores missioniq-backend:latest, missioniq-frontend:latest, pgvector/pgvector:pg16.)

   4B) Public registries (alternative):
       docker pull missioniq/missioniq:backend
       docker pull missioniq/missioniq:frontend
       docker pull pgvector/pgvector:pg16
       docker tag missioniq/missioniq:backend  missioniq-backend:latest
       docker tag missioniq/missioniq:frontend missioniq-frontend:latest
       (If these say unauthorized/denied, the public toggle isn't done; use 4A instead.)

5. VERIFY ARCHITECTURE (must be amd64):
       docker image inspect missioniq-backend:latest  --format "{{.Os}}/{{.Architecture}}"
       docker image inspect missioniq-frontend:latest --format "{{.Os}}/{{.Architecture}}"
   Both must print linux/amd64. If you see arm64, you have the wrong image -> redo Step 4A.

6. LAUNCH:
       cd C:\Users\d-joseph.tashjy\MissionIQ\MissionIQ
       docker compose -f docker-compose.local.yml up -d

7. VERIFY (first boot runs DB migrations + seeds the demo; be patient ~30-60s):
       docker compose -f docker-compose.local.yml logs -f backend
   Wait until you see "[apex]" seed lines and "Uvicorn running". Then health-check:
       curl.exe -s -o NUL -w "api_docs=%{http_code}`n" http://localhost:8000/docs
       curl.exe -s -o NUL -w "login=%{http_code}`n" -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d "{\"email\":\"sarah.mitchell@apexfederal.demo\",\"password\":\"MissionIQ!Demo2026\"}"
       curl.exe -s -o NUL -w "frontend=%{http_code}`n" http://localhost:3000
   Expect: api_docs=200, login=200, frontend=200 or 307.
   Also run: docker compose -f docker-compose.local.yml ps

8. REPORT: print the three URLs, the demo login, which image source you used (4A/4B),
   and container status.

==================== TROUBLESHOOTING (handle, then report) ====================
- "no matching manifest for linux/amd64" or container exits immediately: wrong-arch
  image. Use Step 4A (the *-amd64 archive) and re-verify Step 5.
- Backend exits mentioning MIQ_JWT_SECRET: .env missing/empty -> redo Step 3.
- "image not found" at compose up: the local tags missioniq-backend:latest /
  missioniq-frontend:latest don't exist -> ensure Step 4 (and re-tag in 4B) ran.
- Port 3000 or 8000 already in use: identify the process, report it, offer to stop
  it or change the published port in docker-compose.local.yml.
- Corrupt/stale demo DB: reset and reseed:
      docker compose -f docker-compose.local.yml down -v
      docker compose -f docker-compose.local.yml up -d
- Registry pull unauthorized: a public toggle is incomplete -> use Step 4A.

==================== DELIVERABLE ====================
A short summary: what you did, the running URLs + demo login, which image source
worked, the verified architecture (linux/amd64), and final container status.
```
