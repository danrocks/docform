"""Tests for cross-entity search (backend/routes/search.py).

Verifies the ``/api/search`` endpoint matches across templates, submissions,
and answersets, and that results honour tenant isolation and per-role access
rules (staff only see their own submissions/answersets).
"""

from tests.conftest import (  # answersets_env fixture + helpers live in conftest
    create_answerset,
    seed_template,
    tenant_headers,
    valid_data,
)


def _search(client, token, q, slug="alpha"):
    return client.get(f"/api/search/?q={q}", headers=tenant_headers(slug, token))


class TestSearch:
    def test_requires_query(self, client, admin_token, answersets_env):
        # q has min_length=1; empty -> 422.
        resp = client.get("/api/search/?q=", headers=tenant_headers("alpha", admin_token))
        assert resp.status_code == 422

    def test_matches_template_by_name(self, client, admin_token, answersets_env):
        seed_template(answersets_env, "tenant-a", template_id="tpl-1", name="Invoice Template")
        resp = _search(client, admin_token, "invoice")
        assert resp.status_code == 200
        body = resp.json()
        assert [t["id"] for t in body["templates"]] == ["tpl-1"]
        assert body["total"] >= 1

    def test_matches_answerset_by_data_value_via_submission(self, client, admin_token, answersets_env):
        # Creating an answerset also writes a submission-style JSON file, whose
        # answer values are searchable.
        seed_template(answersets_env, "tenant-a")
        create_answerset(client, admin_token, data=valid_data(customer_name="Zebra Industries"))
        resp = _search(client, admin_token, "zebra")
        assert resp.status_code == 200
        assert resp.json()["submissions"], "expected a submission match on answer value"

    def test_matches_answerset_metadata_by_template_name(self, client, admin_token, answersets_env):
        seed_template(answersets_env, "tenant-a", name="Rental Agreement")
        create_answerset(client, admin_token)
        resp = _search(client, admin_token, "rental")
        assert resp.status_code == 200
        assert resp.json()["answersets"], "expected an answerset metadata match"

    def test_no_match_returns_empty(self, client, admin_token, answersets_env):
        seed_template(answersets_env, "tenant-a", name="Invoice")
        resp = _search(client, admin_token, "nonexistentterm")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["templates"] == [] and body["submissions"] == [] and body["answersets"] == []

    def test_case_insensitive(self, client, admin_token, answersets_env):
        seed_template(answersets_env, "tenant-a", name="Invoice Template")
        assert _search(client, admin_token, "INVOICE").json()["templates"]

    def test_staff_does_not_see_others_answersets(self, client, admin_token, staff_token, answersets_env):
        seed_template(answersets_env, "tenant-a", name="Secret Doc")
        # Owned by admin, not shared with staff.
        create_answerset(client, admin_token)
        resp = _search(client, staff_token, "secret")
        assert resp.status_code == 200
        body = resp.json()
        assert body["submissions"] == []
        assert body["answersets"] == []

    def test_staff_sees_own_answersets(self, client, staff_token, answersets_env):
        seed_template(answersets_env, "tenant-a", name="Staff Doc")
        create_answerset(client, staff_token)
        resp = _search(client, staff_token, "staff doc")
        assert resp.status_code == 200
        assert resp.json()["answersets"], "staff should see their own answersets"

    def test_cross_tenant_isolation(self, client, admin_token, admin_token_tenant_b, answersets_env):
        seed_template(answersets_env, "tenant-a", name="Alpha Only Template")
        create_answerset(client, admin_token)
        # Tenant B searches the same term; must see nothing from tenant A.
        resp = client.get("/api/search/?q=alpha", headers=tenant_headers("beta", admin_token_tenant_b))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0

    def test_requires_auth(self, client, answersets_env):
        resp = client.get("/api/search/?q=x", headers={"Host": "alpha.localhost:3000"})
        assert resp.status_code == 401
