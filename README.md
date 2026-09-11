# Peblo TV Mini

FastAPI + PostgreSQL backend, React CMS, and React viewer for the Peblo TV Mini take-home.

## Run locally

1. Copy `.env.example` to `.env`.
2. Run `docker compose up --build`.
3. Open:
   - API: `http://localhost:8000`
   - CMS: `http://localhost:4173`
   - Viewer: `http://localhost:4174`
4. Log into the CMS with:
   - `editor@peblo.test` / `editor12345`
   - `admin@peblo.test` / `admin12345`

The API container waits for Postgres, runs Alembic migrations, seeds `_given/seed_shows.json`, then starts serving. The bundled seed dataset is publishable out of the box: the seeder materializes the declared sample artwork from `_given/assets`, so you can publish immediately from the CMS after startup. Local artwork is stored on a mounted Docker volume behind the storage abstraction.

## Part D decisions

- `docker-compose.yml` brings up Postgres, API, CMS, and viewer in one command, with persistent DB and storage volumes.
- `.github/workflows/ci.yml` runs backend lint + tests against a Postgres service, builds both frontends, and builds all three Docker images.
- The deploy step is written but intentionally not wired to a cloud account: build, push to a registry, run `alembic upgrade head`, do a rolling restart, then smoke-check `/health` and `/catalog`.
- Secrets are not committed. In production, inject them from a managed secret store such as AWS Secrets Manager, Doppler, or a cloud platform secret manager via environment variables at deploy time. They should never be baked into images or stored in the repo, and each environment should have separate values with rotation.
- The alert I would wire first is: most recent publish run is `failed`, or the pointed-at catalog is older than an acceptable threshold while published content has changed. `/health` proves liveness; this alert catches stale viewer data, which is the correctness failure a user notices.

## Part E answers

- Publishing is atomic because each run writes a versioned catalog file first, then flips `catalog/current.json` to point at it. If the process dies mid-publish, readers still resolve the previous good pointer; startup marks orphaned `running` rows as failed with reason `process died`.
- Moving from local disk to Cloudflare R2 means switching `STORAGE_BACKEND` to `r2` and providing R2 credentials and endpoint settings. The rest of the app talks only to the `Storage` protocol, so the main practical differences are bucket configuration, URL strategy, and CORS on the bucket.
- Search is served from the in-memory published catalog, not from browser-side filtering. That is simple and fast at this data size, but I would move to Postgres full-text or trigram-backed search once the published catalog becomes large enough that memory residency, refresh time, or concurrent search latency are no longer trivial.
- Serving a pre-published catalog file removes DB work from the hot path and makes viewer reads cheap and cacheable. The tradeoff is controlled staleness: publish becomes a required step, per-user personalization is out of scope, and cache invalidation needs explicit operational care.
- Remaining omissions are mainly production polish: no real cloud deploy target, no registry push, and no wired external alerting service. AI tools were used for implementation speed and validation workflow, but code and behavior were checked against running endpoints, tests, and browser verification before being kept.

## Time and scope

- Backend schema, CRUD, publish pipeline, and tests were the bulk of the time.
- CMS and viewer were implemented to the rubric-required surfaces before moving to operability.
- The pipeline work here is optimized for a reviewer being able to run the project cold on a clean machine and inspect the operational decisions directly in the repo.