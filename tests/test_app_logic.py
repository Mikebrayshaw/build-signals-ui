from app_logic import (
    build_opportunity_html,
    classify_source,
    evaluate_password_gate,
    filter_opportunities,
    sort_opportunities,
)


def test_password_gate_missing_password_blocks_access():
    result = evaluate_password_gate(
        is_authenticated=False,
        expected_password=None,
        submitted_password="",
        login_clicked=False,
    )

    assert result.allow_access is False
    assert result.error == "missing_password"


def test_password_gate_success_and_failure_paths():
    fail_result = evaluate_password_gate(
        is_authenticated=False,
        expected_password="secret",
        submitted_password="wrong",
        login_clicked=True,
    )
    success_result = evaluate_password_gate(
        is_authenticated=False,
        expected_password="secret",
        submitted_password="secret",
        login_clicked=True,
    )

    assert fail_result.error == "incorrect_password"
    assert fail_result.allow_access is False

    assert success_result.allow_access is True
    assert success_result.authenticated is True
    assert success_result.should_rerun is True


def test_filter_and_sort_opportunities():
    opportunities = [
        {"title": "Ask HN: API tool", "score": 10, "keywords": ["api"], "comments": 9},
        {"title": "Show HN: Widget", "score": 4, "keywords": ["hardware"], "comments": 20},
        {"title": "Ask HN: Automation", "score": 12, "keywords": ["agent"], "comments": 1},
    ]

    filtered = filter_opportunities(
        opportunities,
        source_filter="Ask HN",
        min_score=8,
        keyword_search="api",
    )
    sorted_items = sort_opportunities(filtered, sort_field="comments", sort_desc=True)

    assert len(filtered) == 1
    assert filtered[0]["title"] == "Ask HN: API tool"
    assert sorted_items[0]["comments"] == 9


def test_classify_source_variants():
    assert classify_source("Ask HN: Need help") == ("source-ask", "Ask HN")
    assert classify_source("Show HN: Built this") == ("source-show", "Show HN")
    assert classify_source("Regular post") == ("", "")


def test_build_opportunity_html_sanitizes_content_and_urls():
    opp = {
        "title": '<script>alert(1)</script> Ask HN',
        "hn_id": "123",
        "score": 5,
        "comments": 2,
        "created_at": "2024-02-01T10:00:00Z",
        "keywords": ["<b>bold</b>", "safe"],
        "github_repos": [
            {"name": '<img src=x onerror=1>', "url": "javascript:alert(1)", "stars": 3},
            "owner/repo",
        ],
    }

    html = build_opportunity_html(opp)

    assert "&lt;script&gt;alert(1)&lt;/script&gt; Ask HN" in html
    assert "javascript:alert(1)" not in html
    assert 'href="#"' in html
    assert "&lt;b&gt;bold&lt;/b&gt;" in html
    assert "&lt;img src=x onerror=1&gt;" in html


def test_build_opportunity_html_respects_keyword_and_repo_limits():
    opp = {
        "title": "Show HN: Something",
        "keywords": ["one", "two", "three"],
        "github_repos": ["a/b", "c/d", "e/f"],
    }

    html = build_opportunity_html(opp, max_keywords=2, max_repos=1)

    assert html.count('class="keyword-tag"') == 2
    assert html.count('class="repo-link"') == 1
