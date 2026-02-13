# Build Signals UI

A Streamlit dashboard for viewing Build Signals opportunities from Hacker News with Supabase-backed identity authentication.

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure secrets

Copy the example secrets file:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml` with your actual values:

```toml
SUPABASE_URL = "https://your-project-id.supabase.co"
SUPABASE_KEY = "your-supabase-anon-key"
# Optional
# AUTH_ALLOWED_ROLES = "admin,analyst"
```

### 3. Run the app

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

## Running tests

Run the automated test suite with:

```bash
pytest
```

## Features

- Supabase Auth email/password login
- Authenticated-only access control
- Optional role-based authorization via `AUTH_ALLOWED_ROLES`
- Current-user indicator and logout action
- Searchable, filterable table of opportunities
- Filter by source type (Ask HN / Show HN)
- Filter by minimum score
- Keyword search
- Sort by score, date, or comments
- Dark theme matching Build Signals branding
- Links to original HN discussions
- Matched GitHub repos with star counts


## Auth configuration

The app now uses **Supabase Auth identities** (instead of a shared global password) for access control.

Required values:

- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Your Supabase anon/public key used by the Streamlit app

Optional values:

- `AUTH_ALLOWED_ROLES` - Comma-separated list of allowed roles (for example: `admin,analyst`).
  - When provided, users must have `user.app_metadata.role` matching one of these values.
  - When omitted, any authenticated Supabase user can access the dashboard.

### Migration from `PASSWORD`

1. Remove `PASSWORD` from your deployment secrets and `.streamlit/secrets.toml`.
2. Ensure email/password auth is enabled in Supabase Auth (Authentication → Providers → Email).
3. Create users in Supabase Auth (Authentication → Users), or allow signups per your org policy.
4. (Optional) Set each user's `app_metadata.role` and configure `AUTH_ALLOWED_ROLES`.
5. Redeploy/restart the Streamlit app so it picks up the new auth settings.

## Deployment

### Streamlit Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Add secrets in the Streamlit Cloud dashboard (Settings > Secrets)
5. Deploy

### Environment Variables

For other deployment platforms, set these environment variables or use the secrets management provided:

- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Your Supabase anon/public key
- `AUTH_ALLOWED_ROLES` (optional) - Comma-separated role allowlist checked against `user.app_metadata.role`
