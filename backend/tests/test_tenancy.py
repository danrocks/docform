import pytest
from tests.conftest import tenant_headers, admin_headers


class TestTenantResolution:
    """Tests 1-4: subdomain → tenant resolution."""

    def test_alpha_subdomain_resolves_to_tenant_a(self, client, admin_token, tenant_a):
        resp = client.get("/api/auth/me", headers=tenant_headers("alpha", admin_token))
        assert resp.status_code == 200
        assert resp.json()["tenant_id"] == "tenant-a"

    def test_nonexistent_subdomain_returns_404(self, client, admin_token):
        resp = client.get(
            "/api/auth/me",
            headers={"Host": "nonexistent.localhost:3000", "Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404
        assert "Organisation not found" in resp.json()["detail"]

    def test_admin_subdomain_returns_none_tenant(self, client, superadmin_token):
        resp = client.get("/api/auth/me", headers=admin_headers(superadmin_token))
        assert resp.status_code == 200
        assert resp.json()["tenant_id"] is None

    def test_bare_domain_login_returns_404(self, client):
        resp = client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "admin123"},
            headers={"Host": "localhost:3000"},
        )
        assert resp.status_code == 404


class TestCrossTenantIsolation:
    """Tests 5-7: cross-tenant data isolation."""

    def test_tenant_a_cannot_see_tenant_b_users(self, client, admin_token, admin_token_tenant_b):
        resp_a = client.get("/api/users", headers=tenant_headers("alpha", admin_token))
        assert resp_a.status_code == 200
        users_a = resp_a.json()["users"]
        for u in users_a:
            assert u.get("tenant_id") == "tenant-a"

        resp_b = client.get("/api/users", headers=tenant_headers("beta", admin_token_tenant_b))
        assert resp_b.status_code == 200
        users_b = resp_b.json()["users"]
        for u in users_b:
            assert u.get("tenant_id") == "tenant-b"

        ids_a = {u["id"] for u in users_a}
        ids_b = {u["id"] for u in users_b}
        assert ids_a.isdisjoint(ids_b)


class TestJWTTenantVerification:
    """Tests 8-10: JWT tenant_id vs subdomain mismatch."""

    def test_tenant_a_token_rejected_on_tenant_b(self, client, admin_token, tenant_b):
        resp = client.get("/api/auth/me", headers=tenant_headers("beta", admin_token))
        assert resp.status_code == 401
        assert "Token not valid" in resp.json()["detail"]

    def test_superadmin_token_rejected_on_tenant_subdomain(self, client, superadmin_token, tenant_a):
        resp = client.get("/api/auth/me", headers=tenant_headers("alpha", superadmin_token))
        assert resp.status_code == 401

    def test_tenant_token_rejected_on_admin_subdomain(self, client, admin_token):
        resp = client.get("/api/auth/me", headers=admin_headers(admin_token))
        assert resp.status_code == 401
        assert "Not authorised" in resp.json()["detail"]


class TestSuperadminTenantManagement:
    """Tests 11-12: superadmin can manage tenants."""

    def test_superadmin_list_tenants(self, client, superadmin_token, tenant_a, tenant_b):
        resp = client.get("/api/tenants", headers=admin_headers(superadmin_token))
        assert resp.status_code == 200
        slugs = {t["slug"] for t in resp.json()}
        assert "alpha" in slugs
        assert "beta" in slugs

    def test_superadmin_create_tenant(self, client, superadmin_token):
        resp = client.post(
            "/api/tenants",
            json={"name": "Gamma Org", "slug": "gamma"},
            headers=admin_headers(superadmin_token),
        )
        assert resp.status_code == 201
        assert resp.json()["slug"] == "gamma"

    def test_create_tenant_reserved_slug_rejected(self, client, superadmin_token):
        resp = client.post(
            "/api/tenants",
            json={"name": "Admin Org", "slug": "admin"},
            headers=admin_headers(superadmin_token),
        )
        assert resp.status_code == 422

    def test_non_superadmin_cannot_manage_tenants(self, client, admin_token):
        resp = client.get(
            "/api/tenants",
            headers=tenant_headers("alpha", admin_token),
        )
        assert resp.status_code == 404


class TestLoginTenantScoping:
    """Tests 13-16: login scoped to tenant subdomain."""

    def test_login_wrong_tenant_fails(self, client, user_repo, tenant_a, tenant_b, seeded_roles):
        from auth_utils import hash_password
        user_repo.create({
            "id": "scoped-user-a",
            "username": "scopeduser",
            "password": hash_password("pass1234"),
            "role": "staff",
            "name": "Scoped A",
            "tenant_id": "tenant-a",
        })
        resp = client.post(
            "/api/auth/login",
            data={"username": "scopeduser", "password": "pass1234"},
            headers={"Host": "beta.localhost:3000"},
        )
        assert resp.status_code == 401
        assert "Incorrect username or password" in resp.json()["detail"]

    def test_same_username_different_tenants(self, client, admin_token, admin_token_tenant_b):
        me_a = client.get("/api/auth/me", headers=tenant_headers("alpha", admin_token))
        me_b = client.get("/api/auth/me", headers=tenant_headers("beta", admin_token_tenant_b))
        assert me_a.status_code == 200
        assert me_b.status_code == 200
        assert me_a.json()["tenant_id"] == "tenant-a"
        assert me_b.json()["tenant_id"] == "tenant-b"
        assert me_a.json()["id"] != me_b.json()["id"]

    def test_login_bare_domain_returns_404(self, client):
        resp = client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "admin123"},
            headers={"Host": "localhost:3000"},
        )
        assert resp.status_code == 404


class TestUserCreationTenantScoping:
    """Test 15: user creation assigns correct tenant_id."""

    def test_create_user_inherits_tenant_id(self, client, admin_token):
        resp = client.post(
            "/api/users",
            json={"username": "newuser01", "password": "password1", "role": "staff", "name": "New User"},
            headers=tenant_headers("alpha", admin_token),
        )
        assert resp.status_code == 201
        assert resp.json()["tenant_id"] == "tenant-a"

    def test_superadmin_creates_user_for_tenant(self, client, superadmin_token, tenant_a):
        resp = client.post(
            "/api/users",
            json={
                "username": "tenantuser",
                "password": "password1",
                "role": "staff",
                "name": "Tenant User",
                "tenant_id": "tenant-a",
            },
            headers=admin_headers(superadmin_token),
        )
        assert resp.status_code == 201
        assert resp.json()["tenant_id"] == "tenant-a"
