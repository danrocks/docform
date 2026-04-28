import pytest


class TestJsonRoleRepository:
    def test_create_and_get_all(self, role_repo):
        role_repo.create({"name": "editor", "description": "Editor"})
        roles = role_repo.get_all()
        assert len(roles) == 1
        assert roles[0]["name"] == "editor"

    def test_get_by_name(self, role_repo):
        role_repo.create({"name": "admin", "description": "Administrator"})
        result = role_repo.get_by_name("admin")
        assert result is not None
        assert result["description"] == "Administrator"

    def test_get_by_name_not_found(self, role_repo):
        assert role_repo.get_by_name("nonexistent") is None

    def test_delete(self, role_repo):
        role_repo.create({"name": "temp", "description": "Temporary"})
        assert role_repo.delete("temp") is True
        assert role_repo.get_by_name("temp") is None

    def test_delete_not_found(self, role_repo):
        assert role_repo.delete("nonexistent") is False

    def test_count(self, role_repo):
        assert role_repo.count() == 0
        role_repo.create({"name": "a", "description": ""})
        role_repo.create({"name": "b", "description": ""})
        assert role_repo.count() == 2


class TestRoleSeeding:
    def test_seeded_roles_exist(self, seeded_roles):
        roles = seeded_roles.get_all()
        names = {r["name"] for r in roles}
        assert names == {"admin", "staff", "approver"}

    def test_seeded_role_count(self, seeded_roles):
        assert seeded_roles.count() == 3


class TestValidateRole:
    def test_valid_role_passes(self, seeded_roles):
        from routes.users import validate_role
        validate_role("admin")

    def test_invalid_role_raises_422(self, seeded_roles):
        from fastapi import HTTPException
        from routes.users import validate_role
        with pytest.raises(HTTPException) as exc_info:
            validate_role("nonexistent")
        assert exc_info.value.status_code == 422
        assert "Invalid role" in exc_info.value.detail


class TestRoleEndpoints:
    def test_list_roles(self, client, admin_token):
        resp = client.get("/api/roles", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        names = {r["name"] for r in resp.json()}
        assert "admin" in names
        assert "staff" in names
        assert "approver" in names

    def test_list_roles_accessible_by_staff(self, client, staff_token):
        resp = client.get("/api/roles", headers={"Authorization": f"Bearer {staff_token}"})
        assert resp.status_code == 200

    def test_list_roles_unauthenticated(self, client):
        resp = client.get("/api/roles")
        assert resp.status_code == 401

    def test_create_role(self, client, admin_token):
        resp = client.post(
            "/api/roles",
            json={"name": "reviewer", "description": "Code reviewer"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "reviewer"

    def test_create_role_duplicate(self, client, admin_token):
        resp = client.post(
            "/api/roles",
            json={"name": "admin", "description": "Dup"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 409

    def test_create_role_staff_forbidden(self, client, staff_token):
        resp = client.post(
            "/api/roles",
            json={"name": "newrole", "description": ""},
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 403

    def test_delete_role(self, client, admin_token):
        client.post(
            "/api/roles",
            json={"name": "temp", "description": "Temporary"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        resp = client.delete("/api/roles/temp", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 204

    def test_delete_role_in_use(self, client, admin_token):
        resp = client.delete("/api/roles/admin", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 409
        assert "user(s) still assigned" in resp.json()["detail"]

    def test_delete_role_not_found(self, client, admin_token):
        resp = client.delete("/api/roles/nonexistent", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404

    def test_delete_role_staff_forbidden(self, client, staff_token):
        resp = client.delete("/api/roles/staff", headers={"Authorization": f"Bearer {staff_token}"})
        assert resp.status_code == 403


class TestUserRoleValidation:
    def test_create_user_invalid_role(self, client, admin_token):
        resp = client.post(
            "/api/users",
            json={"username": "newuser", "password": "pw", "role": "bogus", "name": "X"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422
        assert "Invalid role" in resp.json()["detail"]

    def test_create_user_valid_role(self, client, admin_token):
        resp = client.post(
            "/api/users",
            json={"username": "newuser", "password": "pw", "role": "staff", "name": "X"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201

    def test_update_user_invalid_role(self, client, admin_token, user_repo):
        from auth_utils import hash_password
        user_repo.create({
            "id": "u-upd",
            "username": "updateme",
            "password": hash_password("pw"),
            "role": "staff",
            "name": "Update Me",
        })
        resp = client.put(
            "/api/users/u-upd",
            json={"role": "bogus"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422
        assert "Invalid role" in resp.json()["detail"]

    def test_update_user_valid_role(self, client, admin_token, user_repo):
        from auth_utils import hash_password
        user_repo.create({
            "id": "u-upd2",
            "username": "updateme2",
            "password": hash_password("pw"),
            "role": "staff",
            "name": "Update Me",
        })
        resp = client.put(
            "/api/users/u-upd2",
            json={"role": "approver"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "approver"

    def test_update_user_no_role_skips_validation(self, client, admin_token, user_repo):
        from auth_utils import hash_password
        user_repo.create({
            "id": "u-upd3",
            "username": "updateme3",
            "password": hash_password("pw"),
            "role": "staff",
            "name": "Update Me",
        })
        resp = client.put(
            "/api/users/u-upd3",
            json={"name": "New Name"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"
