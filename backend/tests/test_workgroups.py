import pytest

from tests.conftest import tenant_headers, admin_headers


@pytest.fixture
def approver_token(client, user_repo, tenant_a):
    """Approver token for tenant A (alpha subdomain)."""
    from auth_utils import hash_password
    user_repo.create({
        "id": "test-approver-1",
        "username": "testapprover",
        "password": hash_password("pass1234"),
        "role": "approver",
        "name": "Test Approver",
        "tenant_id": "tenant-a",
    })
    resp = client.post(
        "/api/auth/login",
        data={"username": "testapprover", "password": "pass1234"},
        headers={"Host": "alpha.localhost:3000"},
    )
    return resp.json()["access_token"]


def _create_workgroup(client, admin_token, name="Group A", **extra):
    payload = {"name": name, "description": "", **extra}
    return client.post(
        "/api/workgroups",
        json=payload,
        headers=tenant_headers("alpha", admin_token),
    )


class TestWorkgroupCrud:
    def test_admin_can_create_workgroup(self, client, admin_token):
        resp = _create_workgroup(client, admin_token, name="Marketing")
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Marketing"
        assert body["tenant_id"] == "tenant-a"
        assert body["requires_approval"] is False
        assert body["created_by"] == "test-admin-1"

    def test_admin_can_list_workgroups(self, client, admin_token):
        _create_workgroup(client, admin_token, name="A1")
        _create_workgroup(client, admin_token, name="A2")
        resp = client.get(
            "/api/workgroups",
            headers=tenant_headers("alpha", admin_token),
        )
        assert resp.status_code == 200
        names = sorted(w["name"] for w in resp.json())
        assert names == ["A1", "A2"]

    def test_admin_can_get_update_delete(self, client, admin_token):
        created = _create_workgroup(client, admin_token, name="Old").json()
        wid = created["id"]

        resp = client.get(
            f"/api/workgroups/{wid}",
            headers=tenant_headers("alpha", admin_token),
        )
        assert resp.status_code == 200

        resp = client.put(
            f"/api/workgroups/{wid}",
            json={"name": "New", "requires_approval": True},
            headers=tenant_headers("alpha", admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New"
        assert resp.json()["requires_approval"] is True

        resp = client.delete(
            f"/api/workgroups/{wid}",
            headers=tenant_headers("alpha", admin_token),
        )
        assert resp.status_code == 204

        resp = client.get(
            f"/api/workgroups/{wid}",
            headers=tenant_headers("alpha", admin_token),
        )
        assert resp.status_code == 404

    def test_staff_cannot_manage_workgroups(self, client, staff_token):
        resp = client.get(
            "/api/workgroups",
            headers=tenant_headers("alpha", staff_token),
        )
        assert resp.status_code == 403

        resp = client.post(
            "/api/workgroups",
            json={"name": "Nope"},
            headers=tenant_headers("alpha", staff_token),
        )
        assert resp.status_code == 403

    def test_approver_cannot_manage_workgroups(self, client, approver_token):
        resp = client.post(
            "/api/workgroups",
            json={"name": "Nope"},
            headers=tenant_headers("alpha", approver_token),
        )
        assert resp.status_code == 403

    def test_superadmin_forbidden_from_workgroups(self, client, superadmin_token):
        # Superadmin operates on admin subdomain and cannot manage workgroups.
        resp = client.get(
            "/api/workgroups",
            headers=admin_headers(superadmin_token),
        )
        assert resp.status_code == 403

        resp = client.post(
            "/api/workgroups",
            json={"name": "Nope"},
            headers=admin_headers(superadmin_token),
        )
        assert resp.status_code == 403

    def test_cross_tenant_workgroup_isolation(self, client, admin_token, admin_token_tenant_b):
        _create_workgroup(client, admin_token, name="A only")
        resp = client.get(
            "/api/workgroups",
            headers=tenant_headers("beta", admin_token_tenant_b),
        )
        assert resp.status_code == 200
        assert resp.json() == []


class TestWorkgroupUsers:
    def _make_staff(self, user_repo, user_id="staff-x", username="staffx", tenant_id="tenant-a"):
        from auth_utils import hash_password
        return user_repo.create({
            "id": user_id,
            "username": username,
            "password": hash_password("pass1234"),
            "role": "staff",
            "name": "Staff X",
            "tenant_id": tenant_id,
        })

    def test_add_and_remove_user(self, client, admin_token, user_repo):
        self._make_staff(user_repo)
        wg = _create_workgroup(client, admin_token, name="WG").json()

        resp = client.post(
            f"/api/workgroups/{wg['id']}/users",
            json={"user_id": "staff-x"},
            headers=tenant_headers("alpha", admin_token),
        )
        assert resp.status_code == 201
        assert resp.json() == {"workgroup_id": wg["id"], "user_id": "staff-x"}

        resp = client.get(
            f"/api/workgroups/{wg['id']}/users",
            headers=tenant_headers("alpha", admin_token),
        )
        assert resp.status_code == 200
        assert resp.json() == [{"workgroup_id": wg["id"], "user_id": "staff-x"}]

        resp = client.delete(
            f"/api/workgroups/{wg['id']}/users/staff-x",
            headers=tenant_headers("alpha", admin_token),
        )
        assert resp.status_code == 204

        resp = client.get(
            f"/api/workgroups/{wg['id']}/users",
            headers=tenant_headers("alpha", admin_token),
        )
        assert resp.json() == []

    def test_add_user_from_other_tenant_fails(self, client, admin_token, user_repo, tenant_b):
        self._make_staff(user_repo, user_id="staff-b", username="staffb", tenant_id="tenant-b")
        wg = _create_workgroup(client, admin_token, name="WG").json()
        resp = client.post(
            f"/api/workgroups/{wg['id']}/users",
            json={"user_id": "staff-b"},
            headers=tenant_headers("alpha", admin_token),
        )
        assert resp.status_code == 404


class TestWorkgroupTemplates:
    def test_add_and_remove_template(self, client, admin_token):
        wg = _create_workgroup(client, admin_token, name="WG").json()
        resp = client.post(
            f"/api/workgroups/{wg['id']}/templates",
            json={"template_id": "tpl-1"},
            headers=tenant_headers("alpha", admin_token),
        )
        assert resp.status_code == 201
        assert resp.json() == {"workgroup_id": wg["id"], "template_id": "tpl-1"}

        # TemplateSettings entry should now exist
        ts_resp = client.get(
            "/api/template-settings/tpl-1",
            headers=tenant_headers("alpha", admin_token),
        )
        assert ts_resp.status_code == 200
        assert ts_resp.json()["tenant_id"] == "tenant-a"
        assert ts_resp.json()["restricted_to_workgroups"] is False

        resp = client.get(
            f"/api/workgroups/{wg['id']}/templates",
            headers=tenant_headers("alpha", admin_token),
        )
        assert resp.json() == [{"workgroup_id": wg["id"], "template_id": "tpl-1"}]

        resp = client.delete(
            f"/api/workgroups/{wg['id']}/templates/tpl-1",
            headers=tenant_headers("alpha", admin_token),
        )
        assert resp.status_code == 204

    def test_cascade_delete_workgroup_removes_links(self, client, admin_token, user_repo):
        from auth_utils import hash_password
        user_repo.create({
            "id": "cascade-staff",
            "username": "cascadestaff",
            "password": hash_password("pass1234"),
            "role": "staff",
            "name": "C",
            "tenant_id": "tenant-a",
        })
        wg = _create_workgroup(client, admin_token, name="ToDelete").json()
        wid = wg["id"]
        client.post(
            f"/api/workgroups/{wid}/users",
            json={"user_id": "cascade-staff"},
            headers=tenant_headers("alpha", admin_token),
        )
        client.post(
            f"/api/workgroups/{wid}/templates",
            json={"template_id": "tpl-cascade"},
            headers=tenant_headers("alpha", admin_token),
        )

        resp = client.delete(
            f"/api/workgroups/{wid}",
            headers=tenant_headers("alpha", admin_token),
        )
        assert resp.status_code == 204

        from repositories.factory import (
            get_workgroup_template_repository,
            get_workgroup_user_repository,
        )
        assert get_workgroup_user_repository().get_workgroup_users(wid) == []
        assert get_workgroup_template_repository().get_workgroup_templates(wid) == []


class TestTemplateSettingsEndpoints:
    def test_admin_crud_template_settings(self, client, admin_token):
        resp = client.post(
            "/api/template-settings",
            json={"template_id": "tpl-9", "restricted_to_workgroups": True},
            headers=tenant_headers("alpha", admin_token),
        )
        assert resp.status_code == 201
        assert resp.json()["restricted_to_workgroups"] is True

        resp = client.get(
            "/api/template-settings/tpl-9",
            headers=tenant_headers("alpha", admin_token),
        )
        assert resp.status_code == 200

        resp = client.put(
            "/api/template-settings/tpl-9",
            json={"restricted_to_workgroups": False},
            headers=tenant_headers("alpha", admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["restricted_to_workgroups"] is False

        resp = client.delete(
            "/api/template-settings/tpl-9",
            headers=tenant_headers("alpha", admin_token),
        )
        assert resp.status_code == 204

        resp = client.get(
            "/api/template-settings/tpl-9",
            headers=tenant_headers("alpha", admin_token),
        )
        assert resp.status_code == 404

    def test_staff_cannot_write_template_settings(self, client, staff_token):
        resp = client.post(
            "/api/template-settings",
            json={"template_id": "tpl-x"},
            headers=tenant_headers("alpha", staff_token),
        )
        assert resp.status_code == 403

    def test_superadmin_forbidden_from_template_settings(self, client, superadmin_token):
        resp = client.post(
            "/api/template-settings",
            json={"template_id": "tpl-x"},
            headers=admin_headers(superadmin_token),
        )
        assert resp.status_code == 403

    def test_cascade_delete_settings_clears_workgroup_link(self, client, admin_token):
        wg = _create_workgroup(client, admin_token, name="WG").json()
        client.post(
            f"/api/workgroups/{wg['id']}/templates",
            json={"template_id": "tpl-link"},
            headers=tenant_headers("alpha", admin_token),
        )

        resp = client.delete(
            "/api/template-settings/tpl-link",
            headers=tenant_headers("alpha", admin_token),
        )
        assert resp.status_code == 204

        from repositories.factory import get_workgroup_template_repository
        assert get_workgroup_template_repository().get_workgroup_templates(wg["id"]) == []
