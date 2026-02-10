import os
import logging
import streamlit as st
from supabase import create_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration constants
MAX_KEYWORDS_DISPLAY = 8
MAX_REPOS_DISPLAY = 5
DEFAULT_PAGE_SIZE = 50
CACHE_TTL_SECONDS = 300  # 5 minutes


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
    """Simple password protection."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    # Read PASSWORD from Railway env var first, fallback to Streamlit secrets
    expected_password = os.getenv("PASSWORD") or st.secrets.get("PASSWORD")

    if not expected_password:
        st.error("Missing PASSWORD. Set it in Railway Variables.")
        st.stop()

    if not st.session_state.authenticated:
        st.markdown("## 🏗️ Build Signals")
        st.markdown("Enter password to access the dashboard.")

        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if password == expected_password:
                logger.info("Successful login attempt")
                st.session_state.authenticated = True
                st.rerun()
            else:
                logger.warning("Failed login attempt")
                st.error("Incorrect password")
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


def fetch_opportunities(supabase, limit=None, offset=0):
    """Fetch opportunities from Supabase with optional pagination."""
    try:
        query = supabase.table("opportunities").select("*", count="exact")
        
        if limit:
            query = query.range(offset, offset + limit - 1)
        
        response = query.execute()
        logger.info(f"Fetched {len(response.data)} opportunities from database")
        return response.data, getattr(response, 'count', len(response.data))
    except Exception as e:
        st.error(f"⚠️ Database Error: Failed to fetch opportunities - {str(e)}")
        return [], 0


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
    keywords = opp.get("keywords", []) or []
    github_repos = opp.get("github_repos", []) or []
    created_at = opp.get("created_at", "")

    # Format date
    date_str = ""
    if created_at:
        try:
            date_str = created_at[:10]
        except:
            date_str = ""

    html = f"""
    <div class="opportunity-card">
        <div style="margin-bottom: 8px;">
            <a href="{hn_url}" target="_blank" style="font-size: 16px; font-weight: 500; text-decoration: none;">
                {title}
            </a>
            {f'<span class="source-tag {source_class}">{source_label}</span>' if source_label else ''}
        </div>
        <div style="margin-bottom: 8px;">
            <span class="score-badge">▲ {score}</span>
            <span class="comments-badge">💬 {comments}</span>
            <span style="color: #666; margin-left: 12px; font-size: 13px;">{date_str}</span>
        </div>
    """

    # Keywords
    if keywords:
        html += '<div style="margin-bottom: 8px;">'
        for kw in keywords[:MAX_KEYWORDS_DISPLAY]:  # Limit to MAX_KEYWORDS_DISPLAY
            html += f'<span class="keyword-tag">{kw}</span>'
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

            html += f'''
            <a href="{repo_url}" target="_blank" class="repo-link" style="text-decoration: none;">
                <span style="color: #888;">📦</span>
                <span style="color: #22C55E;">{repo_name}</span>
                {f'<span style="color: #666; margin-left: 8px;">⭐ {stars:,}</span>' if stars else ''}
            </a>
            '''
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
    max_score = max([o.get("score", 0) for o in opportunities]) if opportunities else 100
    min_score = st.sidebar.slider("Minimum Score", 0, max_score, 0)

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

    # Apply filters
    filtered = opportunities

    # Source filter
    if source_filter != "All":
        filtered = [o for o in filtered if source_filter in o.get("title", "")]

    # Score filter
    filtered = [o for o in filtered if o.get("score", 0) >= min_score]

    # Keyword search
    if keyword_search:
        search_lower = keyword_search.lower()
        filtered = [
            o for o in filtered
            if search_lower in o.get("title", "").lower()
            or search_lower in str(o.get("keywords", [])).lower()
        ]

    # Sort
    filtered = sorted(
        filtered,
        key=lambda x: x.get(sort_field, 0) or 0,
        reverse=sort_desc
    )

    # Log filter results
    logger.info(f"Filtered to {len(filtered)} opportunities (from {len(opportunities)} total)")

    # Stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Opportunities", len(filtered))
    with col2:
        avg_score = sum(o.get("score", 0) for o in filtered) / len(filtered) if filtered else 0
        st.metric("Avg Score", f"{avg_score:.0f}")
    with col3:
        with_repos = len([o for o in filtered if o.get("github_repos")])
        st.metric("With GitHub Repos", with_repos)

    st.markdown("---")

    # Calculate pagination
    total_filtered = len(filtered)
    total_pages = (total_filtered + page_size - 1) // page_size

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

    # Slice filtered results for current page
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_opportunities = filtered[start_idx:end_idx]

    # Display paginated opportunities
    if page_opportunities:
        for opp in page_opportunities:
            render_opportunity(opp)
    else:
        st.info("No opportunities match your filters.")

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f"*Showing {len(page_opportunities)} of {len(filtered)} opportunities (Page {page}/{total_pages})*"
    )


if __name__ == "__main__":
    main()
