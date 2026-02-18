import json
import os
import streamlit as st
from supabase import create_client


# Page config
st.set_page_config(
    page_title="Build Signals",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background-color: #0A0A0B;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #111112;
    }

    /* Headers */
    h1, h2, h3 {
        color: #FFFFFF !important;
    }

    /* Accent color for links and highlights */
    a {
        color: #22C55E !important;
    }

    /* Input fields */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div,
    .stMultiSelect > div > div > div {
        background-color: #1A1A1B;
        color: #FFFFFF;
        border-color: #333;
    }

    /* Cards/containers */
    .card {
        background-color: #111112;
        border: 1px solid #222;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }

    .card:hover {
        border-color: #22C55E;
    }

    .score-badge {
        background-color: #22C55E;
        color: #0A0A0B;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
        display: inline-block;
    }

    .badge {
        padding: 4px 8px;
        border-radius: 4px;
        display: inline-block;
        margin-right: 4px;
        font-size: 13px;
    }

    .badge-draft { background-color: #333; color: #FFF; }
    .badge-posted { background-color: #1E3A2F; color: #22C55E; }
    .badge-skipped { background-color: #3B2020; color: #EF4444; }

    .source-tag {
        font-size: 11px;
        padding: 2px 6px;
        border-radius: 4px;
        margin-left: 8px;
    }

    .source-ask { background-color: #3B2F1E; color: #F59E0B; }
    .source-show { background-color: #1E2D3B; color: #3B82F6; }
    .source-ph { background-color: #2D1E3B; color: #A855F7; }
    .source-gh { background-color: #1E3B2D; color: #22C55E; }

    .trend-rising { color: #22C55E; font-weight: bold; }
    .trend-falling { color: #EF4444; }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def _get_secret(key: str):
    """Safely read from st.secrets without crashing when no secrets.toml exists."""
    try:
        return st.secrets[key]
    except Exception:
        return None


def check_password():
    """Simple password protection."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    expected_password = os.getenv("PASSWORD") or _get_secret("PASSWORD")

    if not expected_password:
        st.error("Missing PASSWORD. Set it in Railway Variables.")
        st.stop()

    if not st.session_state.authenticated:
        st.markdown("## 🏗️ Build Signals")
        st.markdown("Enter password to access the dashboard.")

        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if password == expected_password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password")
        return False

    return True


@st.cache_resource
def init_supabase():
    """Initialize read-only Supabase client (anon key)."""
    supabase_url = os.getenv("SUPABASE_URL") or _get_secret("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY") or _get_secret("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        st.error("Missing SUPABASE_URL or SUPABASE_KEY.")
        st.stop()

    return create_client(supabase_url, supabase_key)


@st.cache_resource
def init_supabase_service():
    """Initialize service-role Supabase client for writes (status updates)."""
    supabase_url = os.getenv("SUPABASE_URL") or _get_secret("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_KEY") or _get_secret("SUPABASE_SERVICE_KEY")

    if not supabase_url or not service_key:
        return None  # Writes disabled — no service key configured

    return create_client(supabase_url, service_key)


# ---------------------------------------------------------------------------
# Tab 1: Tweet Drafts
# ---------------------------------------------------------------------------

def render_tweet_drafts(supabase, service_client):
    """Tweet Drafts tab — review, approve, skip generated tweets."""
    st.markdown("### Tweet Drafts")
    st.markdown("*AI-generated tweet drafts from scored signals. Update status to track your queue.*")

    # Filters in sidebar
    status_filter = st.sidebar.selectbox(
        "Status", ["All", "draft", "posted", "skipped"], key="tweet_status"
    )

    # Fetch
    query = supabase.table("tweet_drafts").select("*").order("generated_at", desc=True)
    if status_filter != "All":
        query = query.eq("status", status_filter)
    response = query.limit(100).execute()
    drafts = response.data

    if not drafts:
        st.info("No tweet drafts found." + (" Try changing the status filter." if status_filter != "All" else ""))
        return

    st.markdown(f"**{len(drafts)}** drafts")

    for draft in drafts:
        draft_id = draft["id"]
        status = draft.get("status", "draft")
        status_class = f"badge-{status}" if status in ("draft", "posted", "skipped") else "badge-draft"

        source = draft.get("source", "")
        source_class = {
            "ask_hn": "source-ask", "show_hn": "source-show",
            "producthunt": "source-ph", "github_trending": "source-gh"
        }.get(source, "")
        source_label = {
            "ask_hn": "Ask HN", "show_hn": "Show HN",
            "producthunt": "Product Hunt", "github_trending": "GitHub"
        }.get(source, source)

        title = draft.get("signal_title", "Untitled")
        hook = draft.get("hook", "")
        full_draft = draft.get("full_draft", "")
        word_count = draft.get("word_count", 0)
        relevance = draft.get("relevance_score")
        potential = draft.get("content_potential")
        date_str = (draft.get("generated_at") or "")[:10]

        # Card header
        scores_html = ""
        if relevance is not None:
            scores_html += f'<span class="score-badge">Rel {relevance}</span> '
        if potential is not None:
            scores_html += f'<span class="score-badge" style="background-color:#3B82F6;">Pot {potential}</span> '

        st.markdown(f"""
        <div class="card">
            <div style="margin-bottom:6px;">
                <span class="badge {status_class}">{status.upper()}</span>
                <span class="source-tag {source_class}">{source_label}</span>
                <span style="color:#666; margin-left:12px; font-size:13px;">{date_str}</span>
                <span style="color:#666; margin-left:8px; font-size:13px;">{word_count}w</span>
            </div>
            <div style="margin-bottom:6px; font-weight:500; color:#FFF;">{title}</div>
            {f'<div style="color:#22C55E; font-style:italic; margin-bottom:6px;">"{hook}"</div>' if hook else ''}
            <div style="margin-bottom:8px;">{scores_html}</div>
        </div>
        """, unsafe_allow_html=True)

        # Expandable full draft + status buttons
        with st.expander("View full draft", expanded=False):
            st.text_area("Draft text", full_draft, height=200, key=f"text_{draft_id}", disabled=True)

            if draft.get("signal_url"):
                st.markdown(f"[View original signal]({draft['signal_url']})")

            if service_client:
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("✅ Mark Posted", key=f"post_{draft_id}"):
                        service_client.table("tweet_drafts").update({"status": "posted"}).eq("id", draft_id).execute()
                        st.rerun()
                with col2:
                    if st.button("⏭️ Skip", key=f"skip_{draft_id}"):
                        service_client.table("tweet_drafts").update({"status": "skipped"}).eq("id", draft_id).execute()
                        st.rerun()
                with col3:
                    if st.button("↩️ Reset to Draft", key=f"reset_{draft_id}"):
                        service_client.table("tweet_drafts").update({"status": "draft"}).eq("id", draft_id).execute()
                        st.rerun()
            else:
                st.caption("Add SUPABASE_SERVICE_KEY to enable status updates.")


# ---------------------------------------------------------------------------
# Tab 2: Signals
# ---------------------------------------------------------------------------

def render_signals(supabase):
    """Signals tab — scored opportunities from all sources."""
    st.markdown("### Scored Signals")
    st.markdown("*Opportunities scored by AI for relevance and content potential.*")

    # Sidebar filters
    min_relevance = st.sidebar.slider("Min Relevance Score", 0, 10, 5, key="sig_rel")
    source_filter = st.sidebar.selectbox(
        "Source", ["All", "ask_hn", "show_hn", "producthunt", "github_trending"], key="sig_source"
    )
    sort_choice = st.sidebar.selectbox(
        "Sort by", ["Relevance (High)", "Content Potential (High)", "Newest"], key="sig_sort"
    )

    # Fetch scored signals
    query = (
        supabase.table("opportunities")
        .select("*")
        .not_.is_("relevance_score", "null")
        .gte("relevance_score", min_relevance)
    )
    if source_filter != "All":
        query = query.eq("source", source_filter)

    sort_map = {
        "Relevance (High)": ("relevance_score", True),
        "Content Potential (High)": ("content_potential", True),
        "Newest": ("created_at", True),
    }
    sort_field, sort_desc = sort_map[sort_choice]
    query = query.order(sort_field, desc=sort_desc)

    response = query.limit(100).execute()
    signals = response.data

    if not signals:
        st.info("No scored signals found. Try lowering the relevance threshold.")
        return

    # Stats row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Signals", len(signals))
    with col2:
        avg_rel = sum(s.get("relevance_score", 0) for s in signals) / len(signals)
        st.metric("Avg Relevance", f"{avg_rel:.1f}")
    with col3:
        avg_pot = sum(s.get("content_potential", 0) for s in signals) / len(signals)
        st.metric("Avg Potential", f"{avg_pot:.1f}")

    st.markdown("---")

    for sig in signals:
        title = sig.get("title", "Untitled")
        source = sig.get("source", "")
        source_class = {
            "ask_hn": "source-ask", "show_hn": "source-show",
            "producthunt": "source-ph", "github_trending": "source-gh"
        }.get(source, "")
        source_label = {
            "ask_hn": "Ask HN", "show_hn": "Show HN",
            "producthunt": "Product Hunt", "github_trending": "GitHub"
        }.get(source, source)

        relevance = sig.get("relevance_score", 0)
        potential = sig.get("content_potential", 0)
        category = sig.get("category", "")
        hook = sig.get("one_line_hook", "")
        insight = sig.get("key_insight", "")
        url = sig.get("url", "#")
        score = sig.get("score", 0)
        comments = sig.get("comments", 0)
        date_str = (sig.get("created_at") or "")[:10]

        st.markdown(f"""
        <div class="card">
            <div style="margin-bottom:6px;">
                <a href="{url}" target="_blank" style="font-size:16px; font-weight:500; text-decoration:none;">{title}</a>
                <span class="source-tag {source_class}">{source_label}</span>
            </div>
            <div style="margin-bottom:8px;">
                <span class="score-badge">Rel {relevance}</span>
                <span class="score-badge" style="background-color:#3B82F6;">Pot {potential}</span>
                {f'<span class="badge badge-draft">{category}</span>' if category else ''}
                <span style="color:#666; margin-left:12px; font-size:13px;">▲{score} 💬{comments} · {date_str}</span>
            </div>
            {f'<div style="color:#22C55E; font-style:italic; margin-bottom:4px;">"{hook}"</div>' if hook else ''}
            {f'<div style="color:#AAA; font-size:14px;">{insight}</div>' if insight else ''}
        </div>
        """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Tab 3: Trends
# ---------------------------------------------------------------------------

def render_trends(supabase):
    """Trends tab — Google Trends data for signal keywords."""
    st.markdown("### Google Trends")
    st.markdown("*YoY interest growth for keywords extracted from signals.*")

    # Sidebar filters
    rising_only = st.sidebar.checkbox("Rising trends only", value=False, key="trend_rising")

    query = supabase.table("google_trends").select("*").order("yoy_growth_pct", desc=True)
    if rising_only:
        query = query.eq("is_rising", True)
    response = query.limit(100).execute()
    trends = response.data

    if not trends:
        st.info("No trends data yet. Run the pipeline to populate.")
        return

    # Stats
    rising_count = sum(1 for t in trends if t.get("is_rising"))
    avg_growth = sum(t.get("yoy_growth_pct") or 0 for t in trends) / len(trends)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Keywords Tracked", len(trends))
    with col2:
        st.metric("Rising", rising_count)
    with col3:
        st.metric("Avg YoY Growth", f"{avg_growth:+.0f}%")

    st.markdown("---")

    for trend in trends:
        keyword = trend.get("keyword", "")
        current = trend.get("current_interest")
        year_ago = trend.get("year_ago_interest")
        growth = trend.get("yoy_growth_pct")
        is_rising = trend.get("is_rising", False)
        fetched = (trend.get("fetched_at") or "")[:10]

        growth_str = f"{growth:+.0f}%" if growth is not None else "N/A"
        trend_class = "trend-rising" if is_rising else "trend-falling"

        # Sparkline bar (simple CSS bar chart)
        interest_raw = trend.get("interest_over_time") or []
        interest_data = json.loads(interest_raw) if isinstance(interest_raw, str) else interest_raw
        sparkline_html = ""
        if interest_data:
            max_val = max((p.get("value", 0) for p in interest_data), default=1) or 1
            bars = ""
            for point in interest_data[-12:]:  # last 12 data points
                val = point.get("value", 0)
                height = max(2, int(30 * val / max_val))
                color = "#22C55E" if is_rising else "#666"
                bars += f'<div style="display:inline-block;width:6px;height:{height}px;background:{color};margin-right:1px;vertical-align:bottom;"></div>'
            sparkline_html = f'<div style="display:inline-block;margin-left:16px;height:30px;">{bars}</div>'

        st.markdown(f"""
        <div class="card">
            <div style="display:flex; align-items:center; justify-content:space-between;">
                <div>
                    <span style="font-size:16px; font-weight:500; color:#FFF;">{keyword}</span>
                    <span class="{trend_class}" style="margin-left:12px; font-size:15px;">{growth_str} YoY</span>
                    {sparkline_html}
                </div>
                <div style="text-align:right; color:#666; font-size:13px;">
                    Now: {current if current is not None else '?'} · Year ago: {year_ago if year_ago is not None else '?'} · {fetched}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Expandable related queries
        related_raw = trend.get("related_queries") or []
        related = json.loads(related_raw) if isinstance(related_raw, str) else related_raw
        if related:
            with st.expander(f"Related queries ({len(related)})", expanded=False):
                for rq in related[:10]:
                    if isinstance(rq, dict):
                        st.markdown(f"- **{rq.get('query', '')}** ({rq.get('value', '')})")
                    else:
                        st.markdown(f"- {rq}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not check_password():
        return

    supabase = init_supabase()
    service_client = init_supabase_service()

    st.markdown("# 📡 Build Signals")

    tab1, tab2, tab3 = st.tabs(["🐦 Tweet Drafts", "📊 Signals", "📈 Trends"])

    with tab1:
        render_tweet_drafts(supabase, service_client)

    with tab2:
        render_signals(supabase)

    with tab3:
        render_trends(supabase)

    # Sidebar footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("*[Build Signals](https://buildsignals.co) — AI-powered signal pipeline*")


if __name__ == "__main__":
    main()
