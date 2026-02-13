# Codebase & Tech Stack Audit

## SECTION 1: PROJECT OVERVIEW

This repository is a single-file Streamlit dashboard that reads Build Signals "opportunities" from a Supabase table and renders searchable, filterable cards for Hacker News-derived opportunities. The app enforces a simple shared-password gate before rendering data and uses Streamlit widgets in a sidebar for filtering/sorting/pagination. There is no separate backend service in this repo; data access is done directly from the Streamlit process via the Supabase Python client.

### Repos/directories that are part of this project
- `build-signals-ui` (this repository)
- Top-level directories in this workspace: only `../build-signals-ui` was present during audit (no sibling repo detected)

### Architecture pattern
- **Single-service UI app** (Streamlit monolith) with direct database access to Supabase.

---

## SECTION 2: TECH STACK INVENTORY

```text
Language(s):         Python (app code), TOML (Streamlit config/secrets template)
Frontend:            Streamlit 1.31.1 (Python UI framework)
Backend/API:         None as a standalone API; Streamlit app process handles UI + data fetching
Database:            Supabase (Postgres) via supabase-py 2.3.4 client
Auth:                Custom shared password check via env/secrets + Streamlit session_state
Payments:            None
LLM/AI:              None
Hosting/Deploy:      Procfile present for process-based deploy (e.g., Railway/Heroku-style dyno); README also documents Streamlit Cloud deployment
CI/CD:               None detected (.github/workflows absent)
Email/Notifications: None detected
Other services:      None
```

### Dependency/config files reviewed
- `requirements.txt`
- `Procfile`
- `.streamlit/config.toml`
- `.streamlit/secrets.toml.example`
- `README.md`
- Not present: `package.json`, `pyproject.toml`, `Pipfile`, `Dockerfile`, `docker-compose.yml`, `railway.toml`, `vercel.json`, `fly.toml`, `.github/workflows/*`

---

## SECTION 3: FILE STRUCTURE

```text
build-signals-ui/
├── .gitignore                       # Ignores local secrets, Python env/artifacts, IDE/OS files.
├── .streamlit/
│   ├── config.toml                 # Streamlit server + theme defaults (headless + dark theme colors).
│   └── secrets.toml.example        # Example secret keys for Supabase URL/key and app password.
├── app.py                          # Entire Streamlit app: styling, password auth, Supabase init/query, filters, pagination, card rendering.
├── Procfile                        # Process entrypoint for platform deploy: streamlit run app.py with PORT binding.
├── README.md                       # Setup, features, local run, and deployment notes.
└── requirements.txt                # Python dependencies with pinned versions.
```

---

## SECTION 4: DATABASE SCHEMA

### Database service
- **Supabase Postgres** (inferred from `SUPABASE_URL`, `SUPABASE_KEY`, and `supabase.table("opportunities")` usage).

### Formal schema artifacts found
- No migration files, SQL schema files, ORM models, or schema definition files in this repository.

### Reverse-engineered table usage from code
Only one table is queried:

#### `opportunities` (read-only usage in this repo)
Inferred columns from access patterns:
- `title` (text)
- `hn_id` (string/int convertible to URL query)
- `score` (numeric/int)
- `comments` (numeric/int)
- `keywords` (array-like/json list)
- `github_repos` (array-like/json list of objects or strings)
- `created_at` (timestamp/string)

Relationships/indexes/RLS/constraints:
- Not defined in this repo (no SQL/migrations/policies found).

---

## SECTION 5: ENVIRONMENT VARIABLES

```text
SUPABASE_URL
  Used in: app.py (init_supabase)
  Defined in template: .streamlit/secrets.toml.example
  Purpose: Supabase project URL for client initialization

SUPABASE_KEY
  Used in: app.py (init_supabase)
  Defined in template: .streamlit/secrets.toml.example
  Purpose: Supabase key for client initialization

PASSWORD
  Used in: app.py (check_password)
  Defined in template: .streamlit/secrets.toml.example
  Purpose: Shared dashboard access password

PORT
  Used in: Procfile command (--server.port $PORT)
  Defined in template: Not defined in repo templates
  Purpose: Runtime port injected by hosting platform
```

Notes:
- App prefers environment variables first (`os.getenv`) and falls back to `st.secrets`.
- No `.env`, `.env.example`, or `.env.local` files exist in this repo.

---

## SECTION 6: API ROUTES & ENDPOINTS

- No HTTP API endpoints are defined (no Flask/FastAPI/Express/Next API routes present).
- This is a Streamlit app; user interaction happens through Streamlit widgets, and data is fetched directly from Supabase in-process.

---

## SECTION 7: LLM/AI INTEGRATION

- No LLM provider/client/model usage detected.
- No prompt files and no inline prompt strings detected.

---

## SECTION 8: AUTOMATION & SCHEDULED JOBS

- No scheduled jobs or automation pipelines found.
- No GitHub Actions workflows or cron configs present in this repository.

---

## SECTION 9: AUTHENTICATION & USER MANAGEMENT

- **Auth exists**, but only as **single shared password access**.
- Method: user enters password in Streamlit form; compared to `PASSWORD` env/secret; success stored in `st.session_state.authenticated`.
- No user accounts table/model in this repo.
- No role-based access control.
- No OAuth/email auth flows.
- No billing/subscription gating logic.
- Session management is Streamlit session state only (not JWT/cookie auth framework).

---

## SECTION 10: FRONTEND / UI

### Routes/pages
- One Streamlit app page (`app.py`) with sidebar and main content sections.

### What the page does
- Displays a password login prompt until authenticated.
- Loads opportunities from Supabase table.
- Sidebar controls:
  - Source type filter (All / Ask HN / Show HN)
  - Minimum score slider
  - Keyword text search
  - Sort selector (score/date/comments asc/desc)
  - Pagination size selector
- Main view:
  - Metrics (count, average score, with repos)
  - Page selector
  - Opportunity cards with HN link, score/comments/date, keywords, and GitHub repo links.

### UI/component system
- Streamlit native widgets/components + custom injected CSS via `st.markdown(..., unsafe_allow_html=True)`.
- Dark theme configured in both inline CSS and `.streamlit/config.toml`.

### Responsive/mobile
- Streamlit layout set to `wide`; no explicit mobile-specific layout logic.

### Hardcoded values that should maybe be configurable
- `MAX_KEYWORDS_DISPLAY = 8`
- `MAX_REPOS_DISPLAY = 5`
- Pagination options `[25, 50, 100]`
- CSS color palette values and various UI strings

---

## SECTION 11: DEPLOYMENT STATUS

### Deployment targets/config evidence
- `Procfile` indicates deployment on a process manager platform using command:
  - `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
- README includes Streamlit Cloud deployment instructions.

### Deploy process
- Not automated in repo; appears manual (push to GitHub + configure platform variables/secrets).

### Deployment URL / environments
- No concrete production URL in repo.
- No explicit dev/staging/prod environment config files.

### Current state (from code inspection only)
- App is likely runnable if required env vars/secrets are set and `opportunities` table exists.
- Cannot confirm live runtime health from static audit alone.

---

## SECTION 12: KNOWN ISSUES & TECHNICAL DEBT

### Code quality / reliability observations
- Bare `except:` in date formatting swallows all exceptions in `render_opportunity`.
- `fetch_opportunities` retrieves full table (`select('*')`) before filtering in app memory; could become slow with growth.
- Unused constants: `DEFAULT_PAGE_SIZE`, `CACHE_TTL_SECONDS` declared but not used.
- Logging includes successful/failed login attempts but no rate limiting/lockout.
- Shared password auth is minimal and not user-specific.
- HTML rendered with `unsafe_allow_html=True`; acceptable for controlled content, but risky if untrusted text reaches HTML.

### TODO/FIXME/HACK scan
- No explicit TODO/FIXME/HACK comments found.

### Tests
- No test directory or test files found.

### Security/config concerns
- Security relies on a single shared password and Supabase key from env/secrets.
- No explicit input validation/sanitization for rendered text fields before interpolating HTML.

---

## SECTION 13: CAPABILITY ASSESSMENT

### 1) What can this codebase do TODAY?
- Run a password-protected dashboard.
- Connect to Supabase and read all rows from `opportunities`.
- Let users filter/search/sort/paginate opportunities.
- Show linked HN item and associated GitHub repos with stars when available.

### 2) What's partially built but not working?
- No obviously half-implemented modules/files; app is cohesive.
- Minor partials: unused constants imply planned cache/page-size behavior not fully implemented.

### 3) What's completely missing?
- No API layer.
- No automated tests.
- No CI/CD workflows.
- No formal schema/migrations in repo.
- No user account system, roles, or billing.
- No LLM/AI features in this UI repository.

### 4) Biggest technical risk
- **Scalability risk from full-table fetch + client-side filtering/sorting**: as records grow, performance and memory usage in Streamlit can degrade significantly.

### 5) Change impact for requested future features
- **User profiles**: Not supported cleanly today; would require real auth provider, user table, and per-user state/permissions.
- **Lead scoring**: Architecture can display score fields now, but generating/scoring logic is absent; would likely belong in upstream pipeline/API, then surfaced in UI.
- **Email alerts**: Missing notification service and background scheduler; would require new backend/worker components.
- **Stripe billing**: Not supported; would require auth system + subscription state + webhook handling + feature gating logic.

---

## SUMMARY FOR BUILD PLANNING

- **Tech stack (one line):** Python Streamlit UI (`streamlit==1.31.1`) + Supabase Postgres via `supabase==2.3.4`, with process-based deployment via `Procfile`.
- **Database schema:** Only `opportunities` table is used (fields inferred: title, hn_id, score, comments, keywords, github_repos, created_at); no schema/migrations in repo.
- **What’s deployed and where:** Deployment target is not explicitly pinned; repo supports Streamlit Cloud and Procfile-based platforms (Railway/Heroku-style).
- **What works end-to-end:** Password gate -> Supabase read -> filtered/sorted/paginated opportunity cards in dashboard.
- **What’s broken/missing:** No API service, no tests, no CI/CD, no robust auth/user model, no billing, no background automation.
- **Recommended next technical steps:**
  1. Add server-side querying/pagination to Supabase calls (avoid full-table fetch).
  2. Introduce a formal schema/migrations source of truth (SQL/Prisma/Alembic).
  3. Add automated tests (at least smoke + query/filter logic).
  4. Add CI workflow for lint/type/test checks.
  5. If product requires multi-user + billing, introduce a proper auth/billing backend boundary before feature expansion.
