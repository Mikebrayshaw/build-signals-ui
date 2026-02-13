# Build Signals UI

A Streamlit dashboard for viewing Build Signals opportunities from Hacker News.

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
PASSWORD = "your-secure-password-here"
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

- Password-protected access
- Searchable, filterable table of opportunities
- Filter by source type (Ask HN / Show HN)
- Filter by minimum score
- Keyword search
- Sort by score, date, or comments
- Dark theme matching Build Signals branding
- Links to original HN discussions
- Matched GitHub repos with star counts

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
- `PASSWORD` - Dashboard access password
