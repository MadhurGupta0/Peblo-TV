# Peblo TV Mini — Build Workflow

Working plan for the take-home. Order is dependency-driven: nothing here should be started
before the thing above it works. Check items off as they land.

**Stack (fixed by the brief):** FastAPI + PostgreSQL + SQLAlchemy/Alembic · React + TypeScript
(Vite) × 2 apps · Docker Compose · GitHub Actions.

**Repo root:** `c:\Users\gupta\Desktop\peblo-tv-mini`

---

## 0. Prerequisites — do this first

- [ ] Drop the provided files into `_given/` at the repo root. **They are not on this machine yet.**
  - `_given/seed_shows.json` (95 episode rows, 8 shows)
  - `_given/reference.json` (sections, categories, languages, artwork specs, conventions)
  - `_given/assets/` — `poster_good.jpg`, `poster_wrong_ratio.jpg`, `banner_good.jpg`,
    `banner_too_big.png`, `thumb_good.jpg`, `thumb_tiny.jpg`
  - `_given/CHALLENGE_Peblo_TV_Mini.md`
- [ ] `git init`, first commit of `_given/` + this file. Commit in small, readable steps from here on —
  the commit history is part of what they read.
- [ ] Confirm Docker Desktop is running.

**Nothing below can be designed correctly without reading `reference.json` end to end first.**

---

## 1. Data recon (do before writing any schema) — ~45 min

The brief says the seed data is deliberately imperfect and finding that is part of the exercise.
Do this as a throwaway script (`scripts/recon.py`) and keep its output in the README.

- [ ] Parse `reference.json`. Write down: allowed sections, allowed categories, allowed languages,
      the three artwork specs, and the two conventions (Season 0 = trailers, `content_group` = language variants).
- [ ] Profile `seed_shows.json`:
  - [ ] distinct shows, seasons, episodes; episodes per show
  - [ ] any `section` / `category` / `language` value **not** in `reference.json`
  - [ ] missing / null / zero `duration`
  - [ ] missing `synopsis`, `title`, artwork references
  - [ ] duplicate `(content_group, language)` pairs — this is the uniqueness constraint, so a
        duplicate in seed is a deliberate trap
  - [ ] `content_group`s where one variant is published and the other isn't
  - [ ] `content_group`s spanning different shows/seasons (should be impossible — flag it)
  - [ ] Season 0 rows: are they trailers? any show with Season 0 but no real seasons?
  - [ ] episode numbering gaps / duplicates within a season
  - [ ] shows marked published with no `section`
  - [ ] whitespace / casing inconsistencies in titles and enum-ish fields
- [ ] Write findings to `docs/DATA_FINDINGS.md`. **Decide for each:** reject at seed time, or import
      as-is and let it surface in the validation report. Default answer: **import as-is and surface it** —
      the validation report is worth 15 points of rubric and needs real content.

---

## 2. Part A — Backend (FastAPI + Postgres) — the bulk of the score (60/100)

### 2.1 Skeleton

- [ ] `backend/` — FastAPI app, `uv` or `pip-tools` for deps, ruff + mypy configured.
- [ ] Settings via pydantic-settings, everything from env. No literals.
- [ ] `GET /health` — returns app version, DB reachability, storage reachability, last publish run id.
- [ ] Alembic wired up, `alembic upgrade head` runs on container start.

### 2.2 Schema + migrations (10 pts)

Tables:

- [ ] `shows` — id, slug, title, synopsis, section (nullable), category, status (draft/published), timestamps
- [ ] `seasons` — id, show_id FK, season_number (0 = trailers), title
- [ ] `episodes` — id, season_id FK, episode_number, title, synopsis, duration_seconds,
      language, `content_group`, status, timestamps
- [ ] `artwork` — id, owner_type + owner_id (show or episode), kind (poster/banner/thumbnail),
      storage_key, width, height, bytes, content_type, checksum, uploaded_by, created_at
- [ ] `publish_runs` — id, actor_user_id, started_at, finished_at, status (running/success/failed),
      counts JSONB (shows/episodes/entries), catalogue_key, error, catalogue checksum
- [ ] `users` — id, email, hashed password, role (`editor` | `admin`)

Constraints & indexes — **each one gets a one-line justification in the README:**

- [ ] `UNIQUE (content_group, language)` where content_group is not null — the brief names it explicitly
- [ ] `UNIQUE (season_id, episode_number, language)`
- [ ] `UNIQUE (show_id, season_number)`
- [ ] index on `shows(status, section)` — drives publish + catalogue queries
- [ ] index on `episodes(content_group)` — drives the grouping pass
- [ ] index on `artwork(owner_type, owner_id, kind)` — drives the "has artwork?" check
- [ ] partial index on `publish_runs(status)` for the "is a run in flight" check
- [ ] GIN trigram index on `shows.title` / `episodes.title` if search goes to Postgres (see 2.7)

- [ ] Seeder: `scripts/seed.py` loads `_given/seed_shows.json` idempotently. Also seeds two users
      (`editor@peblo.test`, `admin@peblo.test`) so the reviewer can log in immediately — document the
      passwords in the README.

### 2.3 Auth & roles (part of the 15 API pts) — **must be enforced, not declared**

- [ ] JWT (or signed session) login. `POST /auth/login`, `GET /auth/me`.
- [ ] `require_role("admin")` / `require_role("editor")` as FastAPI dependencies on the routes themselves.
- [ ] editor → all CRUD + upload. admin → CRUD + upload + `POST /admin/catalog/publish`.
- [ ] Anonymous → `GET /catalog`, `GET /catalog/search` only.
- [ ] **Test that an editor token gets 403 on publish.** This is the single most-checked item; write the test.
- [ ] Viewer UI must never hold a token or hit `/admin/*` — explicitly called out as a penalty.

### 2.4 Artwork upload (15 pts)

- [ ] `POST /admin/artwork` — multipart: file, kind, owner_type, owner_id.
- [ ] Validate **server-side** (client-side-only validation is an explicit penalty):
  - size ceiling **200 KB** — check the actual byte count, not the declared one
  - decode with Pillow; reject non-images and corrupt files
  - dimensions + aspect per `reference.json`:
    poster 2:3 ≈ 600×900 · banner 16:9 ≈ 1280×720 · thumbnail 16:9 ≈ 640×360
  - allow a documented tolerance on aspect (e.g. ±1%) and a min/max dimension band; state the rule
- [ ] Errors an editor can act on — structured `{field, code, message}` where message is like:
      *"This poster is 1280×720. Posters must be portrait, about 600×900 (2:3). Try cropping it taller."*
      Never surface a stack trace or a Pillow exception string.
- [ ] Verify against the given assets: `poster_wrong_ratio.jpg` → aspect error,
      `banner_too_big.png` → size error, `thumb_tiny.jpg` → dimension error, the three `*_good` → 200.
      **Turn these six into the upload test suite.**
- [ ] Storage abstraction: `Storage` protocol — `put(key, bytes, content_type) -> None`,
      `get(key)`, `url_for(key)`, `exists(key)`, `delete(key)`.
      Implementations: `LocalDiskStorage` (used here), `R2Storage` (boto3 S3-compatible, written even if
      not exercised). Chosen via `STORAGE_BACKEND` env var. Nothing outside `storage/` may know which is active.

### 2.5 CRUD + validation

- [ ] Shows / seasons / episodes: list, get, create, update, delete. Pagination + filters on the list
      endpoints (section, status, language, `q`) — filters must **compose**, not be mutually exclusive.
- [ ] Business rules enforced at write time where they're cheap, and always re-checked at publish:
  - episode can't be `published` without artwork **and** a duration
  - `(content_group, language)` unique
  - a published show must have a `section`
- [ ] Consistent error envelope across the API. 422 for validation with per-field detail.

### 2.6 Publish job (20 pts — highest-value single item)

- [ ] `POST /admin/catalog/publish` (admin only).
- [ ] Build step:
  - only shows with `status=published` **and** episodes with `status=published`
  - drop shows that end up with zero publishable episodes
  - collapse `content_group` variants into **one** entry with `languages: ["en","hi"]` — pick a
    deterministic canonical variant (document the rule: e.g. lowest language code, or `en` preferred)
  - Season 0 flagged as `trailers`, not emitted as a normal season
  - group by `section`, order deterministically at **every** level (sections by reference.json order,
    shows by title then id, seasons by number, episodes by number) — the same DB state must byte-for-byte
    produce the same file. Assert this in a test.
  - embed `generated_at`, `run_id`, `schema_version`
- [ ] **Atomicity** — never overwrite the live file (explicit penalty):
  - write to a versioned key: `catalog/runs/<run_id>.json`
  - then flip a tiny pointer: `catalog/current.json` containing `{"run_id":..., "key":...}`,
    written via write-temp + atomic rename (local disk) / single PUT (R2)
  - readers resolve pointer → versioned file. A half-written run file is never pointed at.
- [ ] **Recorded:** `publish_runs` row created *before* the build with status `running`; updated to
      `success` (with counts + checksum) or `failed` (with error) at the end.
- [ ] **Crash mid-publish:** the pointer still names the previous good run; the orphaned `running` row is
      reaped on startup (marked `failed`, reason "process died"). Write this up in Part E.
- [ ] **Idempotent:** publishing twice with no data change produces an identical payload (checksum equal);
      record it as a new run but note the no-op. Test it.
- [ ] Concurrency: Postgres advisory lock (or a unique partial index on `status='running'`) so two
      admins can't publish simultaneously. Second caller gets a clean 409.

### 2.7 Read endpoints

- [ ] `GET /catalog` — resolve pointer, serve the published file. ETag / `Cache-Control` on it.
      No DB query in the hot path.
- [ ] `GET /catalog/search?q=&category=&language=&section=` — `q` matches show title **and** episode title
      **and** category; all four filters compose (AND across filters, OR within `q`'s three targets).
  - **Decision to make and document:** in-process index over the loaded catalogue (simple, fine at this
    size) vs Postgres `ILIKE`/trigram vs `tsvector`. Recommended: serve search from the in-memory
    published catalogue, loaded once and refreshed on publish — then state honestly in Part E at what
    size (rows / MB / concurrency) that breaks and that the next step is Postgres FTS, then a search engine.
  - Doing search **in the browser over the whole catalogue with no scale comment** is an explicit penalty.
    Server-side it is.
- [ ] `GET /admin/validation-report` (editor+) — everything currently blocking publish, **grouped for a
      non-engineer**: by show, then by issue type, with the exact fix ("Episode 4 of Season 2 has no
      thumbnail — upload a 640×360 image"). Include the seed-data problems found in step 1.

### 2.8 Tests — "on the parts you consider risky"

Don't chase coverage; cover the risky four and say in the README that that was the choice.

- [ ] Artwork validation — the six given assets + a 199KB/201KB boundary pair.
- [ ] Publish — grouping correctness, determinism/byte-stability, idempotency, exclusion of unpublished,
      Season 0 handling, pointer never points at a partial file.
- [ ] Roles — editor 403 on publish, anon 401 on admin, anon 200 on catalog.
- [ ] Search filter composition — each filter alone and all four together.

---

## 3. Part B — Internal CMS (React + TS) — 15 pts

- [ ] `cms/` — Vite + React + TS + TanStack Query (the brief's default; keep it and say why:
      cache invalidation after publish/upload is the whole problem here).
- [ ] Login screen; token in memory + refresh-safe storage; role read from `/auth/me` and used to
      hide **and** gracefully handle the publish action.
- [ ] **Show/episode list:** search box, filters (section, status, language), pagination. Filters
      reflected in the URL so an editor can bookmark/share a filtered view.
- [ ] **Create/edit form:** three clearly labelled upload slots (Poster 600×900 · Banner 1280×720 ·
      Thumbnail 640×360), each showing required dimensions + max 200 KB up front, a live preview after
      selection, and the server's human-readable error rendered next to the slot.
      Client-side pre-check is a courtesy only — the server is the authority.
- [ ] **Publish page:** the validation report rendered grouped and scannable; a publish button that is
      **disabled with the reasons listed** when blocked; run history table (who, when, counts, outcome,
      duration) with the latest run's catalogue linked.
- [ ] Every screen handles: loading · empty · error (with retry) · permission-denied (an editor opening
      the publish page sees a clear "you need admin" state, not a broken page).
- [ ] Usability bar: *"someone doing this 50 times a week."* Keyboard-submittable forms, no unlabelled
      icons, destructive actions confirmed, success toasts that say what happened.

---

## 4. Part C — Viewer UI (React + TS) — 10 pts

- [ ] `viewer/` — separate app (or clearly separate route). **Reads `/catalog` and `/catalog/search` only.
      No auth, no `/admin/*`.** Enforce it by giving the viewer its own API client with no token logic.
- [ ] **Home:** featured hero using the **banner**; horizontal rows per section using **posters**.
- [ ] **Search + filters** (category, language) with a real empty state ("No shows match Hindi + Songs —
      try clearing a filter"), not a blank screen.
- [ ] **Show detail:** synopsis, seasons → episodes using **thumbnails**, language chips on grouped
      episodes. **Season 0 surfaced as "Trailers", never as a numbered season.**
- [ ] Slow images: fixed aspect-ratio boxes so nothing reflows, `loading="lazy"`, a skeleton/blurred
      placeholder, `decoding="async"`, and a fallback tile on error. Say which you chose and why.
- [ ] Right artwork per surface is explicitly graded — audit each surface before calling it done.

---

## 5. Part D — Pipeline & operability — 10 pts

- [ ] `docker-compose.yml`: `db` (postgres + healthcheck), `api` (waits for db healthy, runs migrations
      then seed then serve), `cms`, `viewer`, and a `minio` or a mounted volume for storage.
- [ ] **`docker compose up` must work first try on a clean machine.** Test it by wiping volumes and
      images and running it cold. This is an explicit penalty item — budget real time for it.
- [ ] `.env.example` — every variable, with a comment each. Nothing secret committed.
- [ ] README paragraph on production secret management (recommended answer: env injected from a managed
      secret store — AWS Secrets Manager / Doppler / GH OIDC → cloud secrets — never in the image, never
      in the repo; rotation and per-environment separation).
- [ ] `.github/workflows/ci.yml`: lint (ruff + eslint + tsc) → backend tests against a Postgres service
      container → build both frontends → build & tag Docker images.
- [ ] Deploy job written out (build → push to registry → migrate → rolling restart → smoke-check
      `/health`), gated behind an environment, **and explained in the README** including why it's not
      wired to a real cloud.
- [ ] **Alerting:** pick one and reason it out. Recommended: alert on *"most recent publish run is
      `failed`, or the pointed-at catalogue is older than N hours while published content has changed"* —
      because a silently stale catalogue is the failure mode a viewer notices and nobody else does.
      Mention `/health` is for liveness, this is for correctness.

---

## 6. Part E — Written (README, max 1 page) — 5 pts

Answer exactly these, tersely:

- [ ] How publishing is atomic; what happens if the process dies mid-publish.
- [ ] The storage abstraction: precisely what changes to move local disk → Cloudflare R2
      (answer: swap `STORAGE_BACKEND`, supply R2 creds/endpoint; `R2Storage` already implements the
      protocol; the only real changes are URL signing and CORS).
- [ ] Search: how it's implemented, the catalogue size at which it stops working, what's next.
- [ ] Why a pre-published file instead of per-request DB queries — and where that bites
      (staleness window, publish becomes a required step, no per-user personalisation, cache invalidation).
- [ ] What was left out and why. Which AI tools were used, where output was accepted vs rejected.
      **Be specific and honest — this is graded as judgment, and a vague answer reads worse than a small scope.**

Also in the README: how to run it, decisions/trade-offs, rough time spent per part.

---

## 7. Stretch — only if time genuinely remains, and say so

- [ ] Rollback to a previous run (nearly free — the pointer already makes this a one-line flip)
- [ ] Publish dry-run showing a diff vs the current catalogue
- [ ] Audit log of who changed what

---

## 8. Delivery

- [ ] Cold-clone into a fresh directory, `docker compose up`, follow your own README literally.
      Fix whatever breaks. Do this before recording anything.
- [ ] Screen recording of the flow: log in as editor → edit a show → upload artwork (show a **rejection**
      with its error, then a success) → open publish page as editor (permission-denied state) →
      log in as admin → validation report → fix a blocker → publish → run history → switch to the viewer →
      hero, rows, search, filter, show detail with trailers + language options. Narrate briefly. ~5 min.
- [ ] Push to a public repo; verify the link works signed-out.

---

## Order of attack (recommended)

1. Recon (§1) — 45 min
2. Schema + migrations + seed (§2.2) — the seed working proves the model fits the data
3. Auth + roles (§2.3) — cheap, and everything else hangs off it
4. Artwork upload + storage (§2.4) — self-contained, 15 pts, testable against given assets
5. CRUD + validation (§2.5)
6. **Publish + catalog + validation report (§2.6–2.7)** — highest value, give it the most care
7. Backend tests (§2.8)
8. CMS (§3)
9. Viewer (§4)
10. Compose + CI (§5) — do a first `docker compose up` early (after step 3) so it isn't a last-day surprise
11. README (§6), cold-run check, recording (§8)

**If time runs short, cut in this order:** stretch goals → CMS polish → viewer polish → test breadth.
**Never cut:** publish atomicity, role enforcement, server-side artwork validation, working compose.
Then write down exactly what was cut and why — the brief says a reasoned 70% beats a rushed 100%.
