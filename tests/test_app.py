import builtins
import importlib
import sys
import types
from contextlib import contextmanager
from datetime import date, datetime
from types import SimpleNamespace

import pytest


class SessionState(dict):
    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError as exc:
            raise AttributeError(item) from exc

    def __setattr__(self, key, value):
        self[key] = value


class FakeStreamlit:
    def __init__(self):
        self.session_state = SessionState()
        self.secrets = {}
        self.errors = []
        self.markdowns = []
        self._text_inputs = []
        self._form_submitted = False
        self.rerun_called = False

    def set_page_config(self, **kwargs):
        return None

    def markdown(self, text, **kwargs):
        self.markdowns.append(text)

    def error(self, text):
        self.errors.append(text)

    def cache_resource(self, fn):
        return fn

    def rerun(self):
        self.rerun_called = True

    @contextmanager
    def form(self, _name):
        yield

    def text_input(self, _label, **kwargs):
        return self._text_inputs.pop(0) if self._text_inputs else ""

    def form_submit_button(self, _label):
        return self._form_submitted


class QueryRecorder:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def select(self, *args, **kwargs):
        self.calls.append(("select", args, kwargs))
        return self

    def ilike(self, *args):
        self.calls.append(("ilike", args, {}))
        return self

    def gte(self, *args):
        self.calls.append(("gte", args, {}))
        return self

    def or_(self, *args):
        self.calls.append(("or_", args, {}))
        return self

    def order(self, *args, **kwargs):
        self.calls.append(("order", args, kwargs))
        return self

    def range(self, *args):
        self.calls.append(("range", args, {}))
        return self

    def execute(self):
        self.calls.append(("execute", (), {}))
        return self.response


class FakeSupabaseClient:
    def __init__(self, query=None, auth=None):
        self._query = query
        self.auth = auth

    def table(self, name):
        assert name == "opportunities"
        return self._query


@pytest.fixture
def app_module(monkeypatch):
    fake_st = FakeStreamlit()
    monkeypatch.setitem(sys.modules, "streamlit", fake_st)
    monkeypatch.setitem(sys.modules, "supabase", types.SimpleNamespace(create_client=lambda *_: None))

    monkeypatch.setattr(builtins, "DEFAULT_PAGE_SIZE", 50, raising=False)
    monkeypatch.setattr(builtins, "MAX_KEYWORDS_DISPLAY", 8, raising=False)
    monkeypatch.setattr(builtins, "MAX_REPOS_DISPLAY", 5, raising=False)

    sys.modules.pop("app", None)
    app = importlib.import_module("app")
    app.datetime = datetime
    app.date = date
    return app, fake_st


def test_fetch_opportunities_applies_filters_sort_and_pagination(app_module):
    app, _ = app_module
    response = SimpleNamespace(data=[{"id": 1}], count=123)
    query = QueryRecorder(response)
    supabase = FakeSupabaseClient(query=query)

    rows, count, err = app.fetch_opportunities(
        supabase,
        source_filter="Ask HN",
        min_score=10,
        keyword_search="api,100%",
        sort_field="created_at",
        sort_desc=False,
        range_start=25,
        range_end=49,
    )

    assert err is None
    assert rows == [{"id": 1}]
    assert count == 123

    assert ("ilike", ("title", "Ask HN:%"), {}) in query.calls
    assert ("gte", ("score", 10), {}) in query.calls
    assert (
        "or_",
        ("title.ilike.%api\\,100\\%%,keywords::text.ilike.%api\\,100\\%%",),
        {},
    ) in query.calls
    assert ("order", ("created_at",), {"desc": False, "nullsfirst": False}) in query.calls
    assert ("range", (25, 49), {}) in query.calls


def test_fetch_opportunities_source_branch_show_hn(app_module):
    app, _ = app_module
    query = QueryRecorder(SimpleNamespace(data=[], count=0))
    supabase = FakeSupabaseClient(query=query)

    app.fetch_opportunities(supabase, source_filter="Show HN")

    assert ("ilike", ("title", "Show HN:%"), {}) in query.calls


def test_check_password_rejects_user_without_allowed_role(app_module, monkeypatch):
    app, fake_st = app_module

    fake_st._text_inputs = ["dev@example.com", "pwd"]
    fake_st._form_submitted = True

    user = SimpleNamespace(email="dev@example.com", app_metadata={"role": "viewer"})
    auth = SimpleNamespace(
        sign_in_with_password=lambda _: SimpleNamespace(
            user=user,
            session=SimpleNamespace(access_token="a", refresh_token="r"),
        ),
        sign_out=lambda: setattr(auth, "signed_out", True),
    )
    auth.signed_out = False

    monkeypatch.setattr(app, "init_supabase", lambda: SimpleNamespace(auth=auth))
    monkeypatch.setenv("AUTH_ALLOWED_ROLES", "admin,operator")

    assert app.check_password() is False
    assert auth.signed_out is True
    assert any("not authorized" in msg for msg in fake_st.errors)


def test_check_password_allows_authorized_user_and_sets_session(app_module, monkeypatch):
    app, fake_st = app_module

    fake_st._text_inputs = ["admin@example.com", "pwd"]
    fake_st._form_submitted = True

    user = SimpleNamespace(email="admin@example.com", app_metadata={"role": "admin"})
    auth = SimpleNamespace(
        sign_in_with_password=lambda _: SimpleNamespace(
            user=user,
            session=SimpleNamespace(access_token="a-token", refresh_token="r-token"),
        ),
        sign_out=lambda: None,
    )

    monkeypatch.setattr(app, "init_supabase", lambda: SimpleNamespace(auth=auth))
    monkeypatch.setenv("AUTH_ALLOWED_ROLES", "admin")

    assert app.check_password() is False
    assert fake_st.rerun_called is True
    assert fake_st.session_state.authenticated is True
    assert fake_st.session_state.auth_user is user
    assert fake_st.session_state.auth_session["access_token"] == "a-token"


def test_check_password_blocks_pre_authenticated_user_with_wrong_role(app_module, monkeypatch):
    app, fake_st = app_module
    fake_st.session_state.authenticated = True
    fake_st.session_state.auth_user = SimpleNamespace(app_metadata={"role": "viewer"})

    monkeypatch.setattr(app, "init_supabase", lambda: SimpleNamespace(auth=SimpleNamespace()))
    monkeypatch.setenv("AUTH_ALLOWED_ROLES", "admin")

    assert app.check_password() is False
    assert any("not authorized" in msg for msg in fake_st.errors)


def test_render_opportunity_regression_payload_shapes_do_not_crash(app_module):
    app, fake_st = app_module

    payload = {
        "title": "Ask HN: Looking for tools",
        "hn_id": "123",
        "score": 42,
        "comments": 5,
        "created_at": "2024-01-01T12:00:00Z",
        "keywords": ["ai", "automation"],
        "github_repos": [
            {"name": "owner/repo", "html_url": "https://github.com/owner/repo", "stargazers_count": 99},
            "another/repo",
        ],
    }

    app.render_opportunity(payload)

    assert fake_st.markdowns
    assert "opportunity-card" in fake_st.markdowns[-1]
