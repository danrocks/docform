"""Tests for bulk answerset document generation (POST /api/answersets/bulk-generate).

Verifies that many answersets can be (re)generated in one request, that each id
is processed independently (per-id status), and that access / tenant rules are
enforced per answerset.
"""

from tests.conftest import create_answerset, seed_template, tenant_headers


def _bulk(client, token, ids, slug="alpha"):
    return client.post(
        "/api/answersets/bulk-generate",
        json={"ids": ids},
        headers=tenant_headers(slug, token),
    )


class TestBulkGenerate:
    def test_generate_multiple(self, client, admin_token, answersets_env):
        seed_template(answersets_env, "tenant-a")
        ids = [create_answerset(client, admin_token).json()["id"] for _ in range(3)]

        resp = _bulk(client, admin_token, ids)
        assert resp.status_code == 200
        body = resp.json()
        assert body["succeeded"] == 3
        assert body["failed"] == 0
        assert {r["status"] for r in body["results"]} == {"generated"}
        assert all(r["docx_path"] for r in body["results"])

    def test_reports_missing_ids(self, client, admin_token, answersets_env):
        seed_template(answersets_env, "tenant-a")
        good = create_answerset(client, admin_token).json()["id"]

        body = _bulk(client, admin_token, [good, "missing-id"]).json()
        assert body["succeeded"] == 1
        assert body["failed"] == 1
        by_id = {r["id"]: r for r in body["results"]}
        assert by_id[good]["status"] == "generated"
        assert by_id["missing-id"]["error"] == "not_found"

    def test_forbidden_for_non_owner_staff(self, client, admin_token, staff_token, answersets_env):
        seed_template(answersets_env, "tenant-a")
        aid = create_answerset(client, admin_token).json()["id"]  # owned by admin
        body = _bulk(client, staff_token, [aid]).json()
        assert body["succeeded"] == 0
        assert body["results"][0]["error"] == "forbidden"

    def test_cross_tenant_not_found(self, client, admin_token, admin_token_tenant_b, answersets_env):
        seed_template(answersets_env, "tenant-a")
        aid = create_answerset(client, admin_token).json()["id"]
        body = _bulk(client, admin_token_tenant_b, [aid], slug="beta").json()
        assert body["results"][0]["error"] == "not_found"

    def test_empty_list(self, client, admin_token, answersets_env):
        resp = _bulk(client, admin_token, [])
        assert resp.status_code == 200
        assert resp.json() == {"results": [], "succeeded": 0, "failed": 0}
