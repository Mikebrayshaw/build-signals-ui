import os
import logging
import html
from datetime import date, datetime
from urllib.parse import urlparse
import streamlit as st
from supabase import create_client

from app_logic import (
    MAX_KEYWORDS_DISPLAY,
    MAX_REPOS_DISPLAY,
    build_opportunity_html,
    evaluate_password_gate,
    filter_opportunities,
    sort_opportunities,
)

DEFAULT_PAGE_SIZE = 50

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

    /* Slider */
    .stSlider > div > div > div > div {
        background-color: #22C55E;
    }

    /* Cards/containers */
    .opportunity-card {
        background-color: #111112;
        border: 1px solid #222;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }

    .opportunity-card:hover {
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

    .comments-badge {
        background-color: #333;
        color: #FFF;
        padding: 4px 8px;
        border-radius: 4px;
        display: inline-block;
        margin-left: 8px;
    }

    .keyword-tag {
        background-color: #1E3A2F;
        color: #22C55E;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        margin-right: 4px;
        display: inline-block;
        margin-bottom: 4px;
    }

    .repo-link {
        background-color: #1A1A1B;
        padding: 8px 12px;
        border-radius: 4px;
        margin-top: 8px;
        display: inline-block;
        margin-right: 8px;
    }

    .source-tag {
        font-size: 11px;
        padding: 2px 6px;
        border-radius: 4px;
        margin-left: 8px;
    }

    .source-ask {
        background-color: #3B2F1E;
        color: #F59E0B;
    }

    .source-show {
        background-color: #1E2D3B;
        color: #3B82F6;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def check_password():
    """Identity-based authentication using Supabase Auth."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "auth_user" not in st.session_state:
        st.session_state.auth_user = None
    if "auth_session" not in st.session_state:
        st.session_state.auth_session = None

    supabase = init_supabase()

    # Restore existing session after rerun/reload
    if st.session_state.auth_session and not st.session_state.auth_user:
        try:
            session_data = st.session_state.auth_session
            supabase.auth.set_session(
                session_data["access_token"],
                session_data["refresh_token"],
            )
            user_response = supabase.auth.get_user()
            st.session_state.auth_user = user_response.user
            st.session_state.authenticated = user_response.user is not None
        except Exception as e:
            logger.warning(f"Failed to restore auth session: {e}")
            st.session_state.authenticated = False
            st.session_state.auth_user = None
            st.session_state.auth_session = None

    allowed_roles = os.getenv("AUTH_ALLOWED_ROLES") or st.secrets.get("AUTH_ALLOWED_ROLES", "")
    allowed_roles = {role.strip() for role in allowed_roles.split(",") if role.strip()}

    # Render login form when no active user is present
    if not st.session_state.authenticated or not st.session_state.auth_user:
        st.markdown("## 🏗️ Build Signals")
        st.markdown("Sign in with your account to access the dashboard.")

        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in")

        if submitted:
            try:
                auth_response = supabase.auth.sign_in_with_password(
                    {"email": email, "password": password}
                )
                user = auth_response.user

                if not user:
                    st.error("Unable to sign in. Check your credentials.")
                    return False

                user_role = (user.app_metadata or {}).get("role")
                if allowed_roles and user_role not in allowed_roles:
                    supabase.auth.sign_out()
                    logger.warning(f"Rejected login for {user.email}; missing required role")
                    st.error("Your account is authenticated but not authorized for this app.")
                    return False

                st.session_state.auth_user = user
                st.session_state.authenticated = True
                st.session_state.auth_session = {
                    "access_token": auth_response.session.access_token,
                    "refresh_token": auth_response.session.refresh_token,
                }
                logger.info(f"Successful login attempt for {user.email}")
                st.rerun()
            except Exception as e:
                logger.warning(f"Failed login attempt: {e}")
                st.error("Incorrect email/password or account unavailable.")

        return False

    # Authorization gate for role-based access (optional)
    if allowed_roles:
        user_role = (st.session_state.auth_user.app_metadata or {}).get("role")
        if user_role not in allowed_roles:
            st.error("You are authenticated but not authorized for this dashboard.")
            return False

    return True



@st.cache_resource
def init_supabase():
    """Initialize Supabase client."""
    # Check env vars first (Railway)
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    # Fall back to st.secrets only if env vars aren't set
    if not supabase_url:
        try:
            supabase_url = st.secrets["SUPABASE_URL"]
        except KeyError:
            st.error("⚠️ Configuration Error: SUPABASE_URL not found in environment or secrets")
            st.stop()
        except Exception as e:
            st.error(f"⚠️ Error reading SUPABASE_URL from secrets: {str(e)}")
            st.stop()

    if not supabase_key:
        try:
            supabase_key = st.secrets["SUPABASE_KEY"]
        except KeyError:
            st.error("⚠️ Configuration Error: SUPABASE_KEY not found in environment or secrets")
            st.stop()
        except Exception as e:
            st.error(f"⚠️ Error reading SUPABASE_KEY from secrets: {str(e)}")
            st.stop()

    if not supabase_url or not supabase_key:
        st.error("Missing SUPABASE_URL or SUPABASE_KEY. Set them in Railway Variables.")
        st.stop()

    logger.info(f"Initializing Supabase connection to {supabase_url[:30]}...")
    return create_client(supabase_url, supabase_key)


def fetch_opportunities(
    supabase,
    source_filter="All",
    min_score=0,
    keyword_search="",
    sort_field="score",
    sort_desc=True,
    range_start=0,
    range_end=DEFAULT_PAGE_SIZE - 1,
):
    """Fetch opportunities from Supabase with server-side filtering, sorting, and pagination."""
    try:
        query = supabase.table("opportunities").select("*", count="exact")

        if source_filter == "Ask HN":
            query = query.ilike("title", "Ask HN:%")
        elif source_filter == "Show HN":
            query = query.ilike("title", "Show HN:%")

        if min_score > 0:
            query = query.gte("score", min_score)

        if keyword_search:
            escaped_search = keyword_search.replace('%', '\\%').replace(',', '\\,')
            query = query.or_(
                f"title.ilike.%{escaped_search}%,keywords::text.ilike.%{escaped_search}%"
            )

        query = query.order(sort_field, desc=sort_desc, nullsfirst=False)
        query = query.range(range_start, range_end)

        response = query.execute()
        total_count = getattr(response, "count", 0) or 0
        logger.info(
            "Fetched %s opportunities from database (%s total matches)",
            len(response.data),
            total_count,
        )
        return response.data, total_count, None
    except Exception as e:
        logger.exception("Database query failed")
        return [], 0, "We couldn't load opportunities right now. Please try again shortly."


def safe_text(value):
    """Escape text for safe HTML rendering."""
    return html.escape(str(value) if value is not None else "")


def is_valid_url(url):
    """Validate URL for rendering clickable links."""
    if not url:
        return False

    parsed = urlparse(str(url))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def render_safe_link(url, label, css_class="", style="", allow_html_label=False):
    """Render either a safe anchor tag or plain text when URL is invalid."""
    safe_label = label if allow_html_label else safe_text(label)
    safe_class = safe_text(css_class)
    safe_style = safe_text(style)

    if is_valid_url(url):
        safe_url = safe_text(url)
        return (
            f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer" '
            f'class="{safe_class}" style="{safe_style}">{safe_label}</a>'
        )

    return f'<span class="{safe_class}" style="{safe_style}">{safe_label}</span>'


def render_opportunity(opp):
    """Render a single opportunity card."""
    # Determine source type and styling
    title = opp.get("title", "Untitled")
    source_class = "source-ask" if "Ask HN" in title else "source-show" if "Show HN" in title else ""
    source_label = "Ask HN" if "Ask HN" in title else "Show HN" if "Show HN" in title else ""

    # Build HN URL
    hn_id = opp.get("hn_id", "")
    hn_url = f"https://news.ycombinator.com/item?id={hn_id}" if hn_id else "#"

    # Get data
    score = opp.get("score", 0)
    comments = opp.get("comments", 0)
    safe_score = safe_text(score)
    safe_comments = safe_text(comments)
    keywords = opp.get("keywords", []) or []
    github_repos = opp.get("github_repos", []) or []
    created_at = opp.get("created_at", "")

    # Format date
    date_str = ""
    if created_at:
        try:
            if isinstance(created_at, str):
                normalized = created_at.replace("Z", "+00:00")
                date_str = datetime.fromisoformat(normalized).date().isoformat()
            elif isinstance(created_at, datetime):
                date_str = created_at.date().isoformat()
            elif isinstance(created_at, date):
                date_str = created_at.isoformat()
            else:
                raise TypeError(f"Unsupported created_at type: {type(created_at).__name__}")
        except (TypeError, ValueError, AttributeError) as exc:
            logger.warning(
                "Could not parse created_at value",
                extra={
                    "created_at_value": repr(created_at),
                    "created_at_type": type(created_at).__name__,
                    "error_type": exc.__class__.__name__,
                },
            )
            date_str = ""

    title_link = render_safe_link(
        hn_url,
        title,
        style="font-size: 16px; font-weight: 500; text-decoration: none;"
    )
    source_badge = (
        f'<span class="source-tag {safe_text(source_class)}">{safe_text(source_label)}</span>'
        if source_label else ''
    )

    html = f"""
    <div class="opportunity-card">
        <div style="margin-bottom: 8px;">
            {title_link}
            {source_badge}
        </div>
        <div style="margin-bottom: 8px;">
            <span class="score-badge">▲ {safe_score}</span>
            <span class="comments-badge">💬 {safe_comments}</span>
            <span style="color: #666; margin-left: 12px; font-size: 13px;">{safe_text(date_str)}</span>
        </div>
    """

    # Keywords
    if keywords:
        html += '<div style="margin-bottom: 8px;">'
        for kw in keywords[:MAX_KEYWORDS_DISPLAY]:  # Limit to MAX_KEYWORDS_DISPLAY
            html += f'<span class="keyword-tag">{safe_text(kw)}</span>'
        html += '</div>'

    # GitHub repos
    if github_repos:
        html += '<div style="margin-top: 12px;">'
        for repo in github_repos[:MAX_REPOS_DISPLAY]:  # Limit to MAX_REPOS_DISPLAY
            if isinstance(repo, dict):
                repo_name = repo.get("name", repo.get("full_name", "Unknown"))
                repo_url = repo.get("url", repo.get("html_url", "#"))
                stars = repo.get("stars", repo.get("stargazers_count", 0))
            else:
                repo_name = str(repo)
                repo_url = f"https://github.com/{repo}"
                stars = 0

            stars_badge = ""
            if stars:
                try:
                    stars_badge = f'<span style="color: #666; margin-left: 8px;">⭐ {int(stars):,}</span>'
                except (TypeError, ValueError):
                    stars_badge = f'<span style="color: #666; margin-left: 8px;">⭐ {safe_text(stars)}</span>'

            repo_label = (
                '<span style="color: #888;">📦</span>'
                f'<span style="color: #22C55E;">{safe_text(repo_name)}</span>'
                f'{stars_badge}'
            )

            html += render_safe_link(
                repo_url,
                repo_label,
                css_class="repo-link",
                style="text-decoration: none;",
                allow_html_label=True
            )
        html += '</div>'

    html += '</div>'

    st.markdown(html, unsafe_allow_html=True)


def main():
    if not check_password():
        return

    # Initialize Supabase
    supabase = init_supabase()

    # Header
    st.markdown("# 📡 Build Signals")
    st.markdown("*Discover opportunities from Hacker News discussions*")

    auth_user = st.session_state.get("auth_user")
    if auth_user:
        user_role = (auth_user.app_metadata or {}).get("role", "user")
        st.caption(f"Signed in as **{auth_user.email}** ({user_role})")

    # Fetch data
    with st.spinner("Loading opportunities..."):
        opportunities, total_count = fetch_opportunities(supabase)

    if not opportunities:
        st.warning("No opportunities found in the database.")
        return

    # Sidebar filters
    st.sidebar.markdown("## Filters")

    # Source type filter
    source_options = ["All", "Ask HN", "Show HN"]
    source_filter = st.sidebar.selectbox("Source Type", source_options)

    # Minimum score filter
    min_score = st.sidebar.number_input("Minimum Score", min_value=0, value=0, step=1)

    # Keyword search
    keyword_search = st.sidebar.text_input("Search Keywords", placeholder="e.g., API, automation")

    # Sort options
    st.sidebar.markdown("## Sort By")
    sort_options = {
        "Score (High to Low)": ("score", True),
        "Score (Low to High)": ("score", False),
        "Date (Newest)": ("created_at", True),
        "Date (Oldest)": ("created_at", False),
        "Comments (Most)": ("comments", True),
        "Comments (Least)": ("comments", False),
    }
    sort_choice = st.sidebar.selectbox("Sort By", list(sort_options.keys()))
    sort_field, sort_desc = sort_options[sort_choice]

    # Pagination settings
    st.sidebar.markdown("## Pagination")
    page_size = st.sidebar.selectbox("Items per page", [25, 50, 100], index=1)

    # Initial count request for pagination controls
    with st.spinner("Loading opportunities..."):
        _, total_count, query_error = fetch_opportunities(
            supabase,
            source_filter=source_filter,
            min_score=min_score,
            keyword_search=keyword_search,
            sort_field=sort_field,
            sort_desc=sort_desc,
            range_start=0,
            range_end=0,
        )

    if query_error:
        st.error(query_error)
        return

    if total_count == 0:
        st.info("No opportunities match your current filters. Try broadening your search.")
        return

    total_pages = max(1, (total_count + page_size - 1) // page_size)

    # Page selector
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        page = st.number_input(
            "Page", 
            min_value=1, 
            max_value=max(1, total_pages), 
            value=1,
            help=f"Total pages: {total_pages}"
        )

    # Fetch only current page
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_opportunities, _, query_error = fetch_opportunities(
        supabase,
        source_filter=source_filter,
        min_score=min_score,
        keyword_search=keyword_search,
        sort_field=sort_field,
        sort_desc=sort_desc,
        range_start=start_idx,
        range_end=end_idx - 1,
    )

    if query_error:
        st.error(query_error)
        return

    # Stats from current page + global match count
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Opportunities", total_count)
    with col2:
        avg_score = sum(o.get("score", 0) for o in page_opportunities) / len(page_opportunities) if page_opportunities else 0
        st.metric("Avg Score (Page)", f"{avg_score:.0f}")
    with col3:
        with_repos = len([o for o in page_opportunities if o.get("github_repos")])
        st.metric("With GitHub Repos (Page)", with_repos)

    st.markdown("---")

    # Display paginated opportunities
    if page_opportunities:
        for opp in page_opportunities:
            render_opportunity(opp)
    else:
        st.info("No opportunities match your filters.")

    # Footer
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout"):
        try:
            supabase.auth.sign_out()
        except Exception as e:
            logger.warning(f"Error while signing out: {e}")
        st.session_state.authenticated = False
        st.session_state.auth_user = None
        st.session_state.auth_session = None
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f"*Showing {len(page_opportunities)} of {total_count} opportunities (Page {page}/{total_pages})*"
    )


if __name__ == "__main__":
    main()
