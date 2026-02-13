"""Pure business logic helpers for Build Signals UI."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any
from urllib.parse import urlparse

MAX_KEYWORDS_DISPLAY = 8
MAX_REPOS_DISPLAY = 5


@dataclass(frozen=True)
class PasswordGateResult:
    authenticated: bool
    allow_access: bool
    error: str | None = None
    should_rerun: bool = False


def evaluate_password_gate(
    *,
    is_authenticated: bool,
    expected_password: str | None,
    submitted_password: str,
    login_clicked: bool,
) -> PasswordGateResult:
    """Evaluate password-gate state without UI dependencies."""
    if not expected_password:
        return PasswordGateResult(False, False, error="missing_password")

    if is_authenticated:
        return PasswordGateResult(True, True)

    if not login_clicked:
        return PasswordGateResult(False, False)

    if submitted_password == expected_password:
        return PasswordGateResult(True, True, should_rerun=True)

    return PasswordGateResult(False, False, error="incorrect_password")


def classify_source(title: str) -> tuple[str, str]:
    """Return CSS class and label for known HN source tags."""
    if "Ask HN" in title:
        return "source-ask", "Ask HN"
    if "Show HN" in title:
        return "source-show", "Show HN"
    return "", ""


def safe_date(created_at: Any) -> str:
    if isinstance(created_at, str) and created_at:
        return created_at[:10]
    return ""


def sanitize_url(url: Any) -> str:
    """Allow only http(s) absolute urls and root-relative urls."""
    if not isinstance(url, str) or not url:
        return "#"

    parsed = urlparse(url)
    if parsed.scheme in {"http", "https"}:
        return url
    if parsed.scheme == "" and url.startswith("/"):
        return url
    return "#"


def filter_opportunities(
    opportunities: list[dict[str, Any]],
    *,
    source_filter: str,
    min_score: int,
    keyword_search: str,
) -> list[dict[str, Any]]:
    filtered = opportunities

    if source_filter != "All":
        filtered = [o for o in filtered if source_filter in o.get("title", "")]

    filtered = [o for o in filtered if o.get("score", 0) >= min_score]

    if keyword_search:
        search_lower = keyword_search.lower()
        filtered = [
            o
            for o in filtered
            if search_lower in o.get("title", "").lower()
            or search_lower in str(o.get("keywords", [])).lower()
        ]

    return filtered


def sort_opportunities(
    opportunities: list[dict[str, Any]],
    *,
    sort_field: str,
    sort_desc: bool,
) -> list[dict[str, Any]]:
    return sorted(
        opportunities,
        key=lambda x: x.get(sort_field, 0) or 0,
        reverse=sort_desc,
    )


def build_opportunity_html(
    opp: dict[str, Any],
    *,
    max_keywords: int = MAX_KEYWORDS_DISPLAY,
    max_repos: int = MAX_REPOS_DISPLAY,
) -> str:
    title = escape(str(opp.get("title", "Untitled")))
    source_class, source_label = classify_source(str(opp.get("title", "")))

    hn_id = opp.get("hn_id", "")
    hn_url = sanitize_url(f"https://news.ycombinator.com/item?id={hn_id}") if hn_id else "#"

    score = opp.get("score", 0)
    comments = opp.get("comments", 0)
    keywords = opp.get("keywords", []) or []
    github_repos = opp.get("github_repos", []) or []
    date_str = escape(safe_date(opp.get("created_at", "")))

    html = f'''
    <div class="opportunity-card">
        <div style="margin-bottom: 8px;">
            <a href="{hn_url}" target="_blank" style="font-size: 16px; font-weight: 500; text-decoration: none;">
                {title}
            </a>
            {f'<span class="source-tag {source_class}">{escape(source_label)}</span>' if source_label else ''}
        </div>
        <div style="margin-bottom: 8px;">
            <span class="score-badge">▲ {score}</span>
            <span class="comments-badge">💬 {comments}</span>
            <span style="color: #666; margin-left: 12px; font-size: 13px;">{date_str}</span>
        </div>
    '''

    if keywords:
        html += '<div style="margin-bottom: 8px;">'
        for kw in keywords[:max_keywords]:
            html += f'<span class="keyword-tag">{escape(str(kw))}</span>'
        html += "</div>"

    if github_repos:
        html += '<div style="margin-top: 12px;">'
        for repo in github_repos[:max_repos]:
            if isinstance(repo, dict):
                repo_name = escape(str(repo.get("name", repo.get("full_name", "Unknown"))))
                repo_url = sanitize_url(repo.get("url", repo.get("html_url", "#")))
                stars = repo.get("stars", repo.get("stargazers_count", 0))
            else:
                repo_name = escape(str(repo))
                repo_url = sanitize_url(f"https://github.com/{repo}")
                stars = 0

            html += f'''
            <a href="{repo_url}" target="_blank" class="repo-link" style="text-decoration: none;">
                <span style="color: #888;">📦</span>
                <span style="color: #22C55E;">{repo_name}</span>
                {f'<span style="color: #666; margin-left: 8px;">⭐ {stars:,}</span>' if stars else ''}
            </a>
            '''
        html += "</div>"

    html += "</div>"
    return html
