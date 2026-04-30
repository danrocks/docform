import pytest


class TestListUsers:
    def test_list_users_as_admin(self, client, admin_token):
        resp = client.get("/api/users", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        assert isinstance(data["users"], list)
        assert data["total"] >= 1

    def test_list_users_as_staff_forbidden(self, client, staff_token):
        resp = client.get("/api/users", headers={"Authorization": f"Bearer {staff_token}"})
        assert resp.status_code == 403

    def test_list_users_unauthenticated(self, client):
        resp = client.get("/api/users")
        assert resp.status_code == 401

    def test_list_users_pagination(self, client, admin_token, user_repo, seeded_roles):
        from auth_utils import hash_password

        for i in range(5):
            user_repo.create({
                "id": f"pag-user-{i}",
                "username": f"paguser{i}",
                "password": hash_password("pw"),
                "role": "staff",
                "name": f"Pag User {i}",
            })
        resp = client.get(
            "/api/users?skip=1&limit=2",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["users"]) == 2
        assert data["skip"] == 1
        assert data["limit"] == 2
        assert data["total"] >= 5


class TestGetUser:
    def test_get_user_by_id(self, client, admin_token, user_repo):
        from auth_utils import hash_password

        user_repo.create({
            "id": "get-user-1",
            "username": "getme",
            "password": hash_password("pw"),
            "role": "staff",
            "name": "Get Me",
        })
        resp = client.get(
            "/api/users/get-user-1",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "get-user-1"
        assert data["username"] == "getme"
        assert data["name"] == "Get Me"
        assert "password" not in data

    def test_get_user_not_found(self, client, admin_token):
        resp = client.get(
            "/api/users/nonexistent-id",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    def test_get_user_as_staff_forbidden(self, client, staff_token):
        resp = client.get(
            "/api/users/test-staff-1",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 403


class TestCreateUser:
    def test_create_user(self, client, admin_token):
        resp = client.post(
            "/api/users",
            json={"username": "newcreated", "password": "pw", "role": "staff", "name": "New User"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "newcreated"
        assert "password" not in data

    def test_create_user_duplicate_username(self, client, admin_token):
        client.post(
            "/api/users",
            json={"username": "dupuser", "password": "pw", "role": "staff", "name": "Dup"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        resp = client.post(
            "/api/users",
            json={"username": "dupuser", "password": "pw", "role": "staff", "name": "Dup2"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 409

    def test_create_user_as_staff_forbidden(self, client, staff_token):
        resp = client.post(
            "/api/users",
            json={"username": "staffcreated", "password": "pw", "role": "staff", "name": "X"},
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 403


class TestUpdateUser:
    def _create_test_user(self, user_repo, user_id="upd-user-1", username="upduser"):
        from auth_utils import hash_password

        user_repo.create({
            "id": user_id,
            "username": username,
            "password": hash_password("pw"),
            "role": "staff",
            "name": "Update Target",
        })

    def test_update_user_name(self, client, admin_token, user_repo):
        self._create_test_user(user_repo)
        resp = client.put(
            "/api/users/upd-user-1",
            json={"name": "New Name"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    def test_update_user_password(self, client, admin_token, user_repo):
        self._create_test_user(user_repo, user_id="upd-pw-1", username="updpwuser")
        resp = client.put(
            "/api/users/upd-pw-1",
            json={"password": "newpass"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        # Verify login with new password
        login_resp = client.post(
            "/api/auth/login",
            data={"username": "updpwuser", "password": "newpass"},
        )
        assert login_resp.status_code == 200

    def test_update_user_username_conflict(self, client, admin_token, user_repo):
        self._create_test_user(user_repo, user_id="upd-conf-1", username="conflictuser1")
        self._create_test_user(user_repo, user_id="upd-conf-2", username="conflictuser2")
        resp = client.put(
            "/api/users/upd-conf-2",
            json={"username": "conflictuser1"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]

    def test_update_user_not_found(self, client, admin_token):
        resp = client.put(
            "/api/users/nonexistent-id",
            json={"name": "X"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    def test_update_user_self_role_change_blocked(self, client, admin_token):
        resp = client.put(
            "/api/users/test-admin-1",
            json={"role": "staff"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 409
        assert "Cannot change your own role" in resp.json()["detail"]


class TestDeleteUser:
    def test_delete_user(self, client, admin_token, user_repo):
        from auth_utils import hash_password

        user_repo.create({
            "id": "del-user-1",
            "username": "delme",
            "password": hash_password("pw"),
            "role": "staff",
            "name": "Del Me",
        })
        resp = client.delete(
            "/api/users/del-user-1",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 204

    def test_delete_user_not_found(self, client, admin_token):
        resp = client.delete(
            "/api/users/nonexistent-id",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    def test_delete_self_blocked(self, client, admin_token):
        resp = client.delete(
            "/api/users/test-admin-1",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 409
        assert "Cannot delete your own account" in resp.json()["detail"]

    def test_delete_user_as_staff_forbidden(self, client, staff_token):
        resp = client.delete(
            "/api/users/test-admin-1",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 403


class TestChangePassword:
    def test_change_own_password(self, client, admin_token):
        resp = client.put(
            "/api/auth/me/password",
            json={"current_password": "pass123", "new_password": "newpass456"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Password updated successfully"
        # Verify login with new password
        login_resp = client.post(
            "/api/auth/login",
            data={"username": "testadmin", "password": "newpass456"},
        )
        assert login_resp.status_code == 200

    def test_change_password_wrong_current(self, client, admin_token):
        resp = client.put(
            "/api/auth/me/password",
            json={"current_password": "wrongpass", "new_password": "newpass"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 400
        assert "Current password is incorrect" in resp.json()["detail"]

    def test_change_password_unauthenticated(self, client):
        resp = client.put(
            "/api/auth/me/password",
            json={"current_password": "pw", "new_password": "newpw"},
        )
        assert resp.status_code == 401


class TestUpdateRole:
    def test_update_role_description(self, client, admin_token):
        resp = client.put(
            "/api/roles/admin",
            json={"description": "Updated admin description"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated admin description"
        assert resp.json()["name"] == "admin"

    def test_update_role_not_found(self, client, admin_token):
        resp = client.put(
            "/api/roles/nonexistent",
            json={"description": "X"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    def test_update_role_as_staff_forbidden(self, client, staff_token):
        resp = client.put(
            "/api/roles/admin",
            json={"description": "Hacked"},
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 403
