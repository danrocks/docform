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
                "password": hash_password("password1"),
                "role": "staff",
                "name": f"Pag User {i}",
            "tenant_id": "tenant-a",
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
            "password": hash_password("password1"),
            "role": "staff",
            "name": "Get Me",
            "tenant_id": "tenant-a",
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
            json={"username": "newcreated", "password": "password1", "role": "staff", "name": "New User"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "newcreated"
        assert "password" not in data

    def test_create_user_duplicate_username(self, client, admin_token):
        client.post(
            "/api/users",
            json={"username": "dupuser", "password": "password1", "role": "staff", "name": "Dup"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        resp = client.post(
            "/api/users",
            json={"username": "dupuser", "password": "password1", "role": "staff", "name": "Dup2"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 409

    def test_create_user_as_staff_forbidden(self, client, staff_token):
        resp = client.post(
            "/api/users",
            json={"username": "staffcreated", "password": "password1", "role": "staff", "name": "X"},
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 403


class TestUpdateUser:
    def _create_test_user(self, user_repo, user_id="upd-user-1", username="upduser"):
        from auth_utils import hash_password

        user_repo.create({
            "id": user_id,
            "username": username,
            "password": hash_password("password1"),
            "role": "staff",
            "name": "Update Target",
            "tenant_id": "tenant-a",
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
            json={"password": "newpass12"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        # Verify login with new password
        login_resp = client.post(
            "/api/auth/login",
            data={"username": "updpwuser", "password": "newpass12"},
            headers={"Host": "alpha.localhost:3000"},
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
            "password": hash_password("password1"),
            "role": "staff",
            "name": "Del Me",
            "tenant_id": "tenant-a",
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
            json={"current_password": "pass1234", "new_password": "newpass456"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Password updated successfully"
        # Verify login with new password
        login_resp = client.post(
            "/api/auth/login",
            data={"username": "testadmin", "password": "newpass456"},
            headers={"Host": "alpha.localhost:3000"},
        )
        assert login_resp.status_code == 200

    def test_change_password_wrong_current(self, client, admin_token):
        resp = client.put(
            "/api/auth/me/password",
            json={"current_password": "wrongpass", "new_password": "newpass12"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 400
        assert "Current password is incorrect" in resp.json()["detail"]

    def test_change_password_unauthenticated(self, client):
        resp = client.put(
            "/api/auth/me/password",
            json={"current_password": "password1", "new_password": "newpass12"},
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


# --- Point 2: Password strength validation ---

class TestPasswordValidation:
    def test_create_user_short_password(self, client, admin_token):
        resp = client.post(
            "/api/users",
            json={"username": "shortpw", "password": "abc", "role": "staff", "name": "X"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422

    def test_update_user_short_password(self, client, admin_token, user_repo):
        from auth_utils import hash_password
        user_repo.create({
            "id": "pw-val-1",
            "username": "pwvaluser",
            "password": hash_password("password1"),
            "role": "staff",
            "name": "PW Val",
            "tenant_id": "tenant-a",
        })
        resp = client.put(
            "/api/users/pw-val-1",
            json={"password": "short"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422

    def test_change_own_password_short_new(self, client, admin_token):
        resp = client.put(
            "/api/auth/me/password",
            json={"current_password": "pass1234", "new_password": "short"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422

    def test_configurable_min_length(self, client, admin_token, monkeypatch):
        from config import settings
        monkeypatch.setattr(settings, "MIN_PASSWORD_LENGTH", 12)
        resp = client.post(
            "/api/users",
            json={"username": "minlen12", "password": "eightchr", "role": "staff", "name": "X"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422


# --- Point 3: Username format validation ---

class TestUsernameValidation:
    def test_create_user_short_username(self, client, admin_token):
        resp = client.post(
            "/api/users",
            json={"username": "ab", "password": "password1", "role": "staff", "name": "X"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422

    def test_create_user_spaces_in_username(self, client, admin_token):
        resp = client.post(
            "/api/users",
            json={"username": "bad user", "password": "password1", "role": "staff", "name": "X"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422

    def test_create_user_special_chars_username(self, client, admin_token):
        resp = client.post(
            "/api/users",
            json={"username": "bad@!#", "password": "password1", "role": "staff", "name": "X"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422

    def test_create_user_valid_username(self, client, admin_token):
        resp = client.post(
            "/api/users",
            json={"username": "valid-user_1", "password": "password1", "role": "staff", "name": "Valid"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201


# --- Point 4: Rate limiting ---

class TestRateLimit:
    def test_fifth_failed_login_still_allowed(self, client, user_repo, tenant_a):
        from auth_utils import hash_password
        import rate_limit
        rate_limit._attempts.clear()

        user_repo.create({
            "id": "rate-user-1",
            "username": "rateuser",
            "password": hash_password("password1"),
            "role": "staff",
            "name": "Rate User",
            "tenant_id": "tenant-a",
        })
        for _ in range(5):
            resp = client.post("/api/auth/login", data={"username": "rateuser", "password": "wrong1234"}, headers={"Host": "alpha.localhost:3000"})
            assert resp.status_code == 401

    def test_sixth_failed_login_blocked(self, client, user_repo, tenant_a):
        from auth_utils import hash_password
        import rate_limit
        rate_limit._attempts.clear()

        user_repo.create({
            "id": "rate-user-2",
            "username": "rateuser2",
            "password": hash_password("password1"),
            "role": "staff",
            "name": "Rate User 2",
            "tenant_id": "tenant-a",
        })
        for _ in range(5):
            client.post("/api/auth/login", data={"username": "rateuser2", "password": "wrong1234"}, headers={"Host": "alpha.localhost:3000"})

        resp = client.post("/api/auth/login", data={"username": "rateuser2", "password": "wrong1234"}, headers={"Host": "alpha.localhost:3000"})
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers

    def test_successful_login_resets_counter(self, client, user_repo, tenant_a):
        from auth_utils import hash_password
        import rate_limit
        rate_limit._attempts.clear()

        user_repo.create({
            "id": "rate-user-3",
            "username": "rateuser3",
            "password": hash_password("password1"),
            "role": "staff",
            "name": "Rate User 3",
            "tenant_id": "tenant-a",
        })
        for _ in range(4):
            client.post("/api/auth/login", data={"username": "rateuser3", "password": "wrong1234"}, headers={"Host": "alpha.localhost:3000"})

        resp = client.post("/api/auth/login", data={"username": "rateuser3", "password": "password1"}, headers={"Host": "alpha.localhost:3000"})
        assert resp.status_code == 200

        # After reset, failures should count from zero again
        for _ in range(5):
            resp = client.post("/api/auth/login", data={"username": "rateuser3", "password": "wrong1234"}, headers={"Host": "alpha.localhost:3000"})
            assert resp.status_code == 401


# --- Point 5: Token revocation / logout ---

class TestLogout:
    def test_logout_revokes_token(self, client, admin_token):
        import auth_utils
        auth_utils._revoked_jtis.clear()

        resp = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Logged out successfully"

        # Using the same token on a protected endpoint should fail
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 401

    def test_logout_without_auth(self, client):
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 401


# --- Point 7: Public user info ---

class TestPublicUserInfo:
    def test_staff_can_view_public_info(self, client, staff_token, user_repo):
        from auth_utils import hash_password
        user_repo.create({
            "id": "pub-user-1",
            "username": "pubuser",
            "password": hash_password("password1"),
            "role": "staff",
            "name": "Public User",
            "tenant_id": "tenant-a",
        })
        resp = client.get(
            "/api/users/pub-user-1/public",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data == {"id": "pub-user-1", "name": "Public User", "role": "staff"}
        assert "username" not in data
        assert "password" not in data

    def test_staff_cannot_view_full_user(self, client, staff_token):
        resp = client.get(
            "/api/users/test-admin-1",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 403

    def test_admin_can_view_full_user(self, client, admin_token, user_repo):
        from auth_utils import hash_password
        user_repo.create({
            "id": "full-user-1",
            "username": "fulluser",
            "password": hash_password("password1"),
            "role": "staff",
            "name": "Full User",
            "tenant_id": "tenant-a",
        })
        resp = client.get(
            "/api/users/full-user-1",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "full-user-1"
        assert data["username"] == "fulluser"
        assert "password" not in data

    def test_public_user_not_found(self, client, staff_token):
        resp = client.get(
            "/api/users/nonexistent/public",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert resp.status_code == 404

    def test_public_user_unauthenticated(self, client):
        resp = client.get("/api/users/test-admin-1/public")
        assert resp.status_code == 401


# --- Point 8: Pagination ---

class TestPaginationExtended:
    def test_pagination_skip_limit(self, client, admin_token, user_repo):
        from auth_utils import hash_password
        for i in range(5):
            user_repo.create({
                "id": f"pag2-user-{i}",
                "username": f"pag2user{i}",
                "password": hash_password("password1"),
                "role": "staff",
                "name": f"Pag2 User {i}",
            "tenant_id": "tenant-a",
            })
        resp = client.get(
            "/api/users?skip=1&limit=2",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["users"]) == 2
        assert data["total"] >= 5
        assert data["skip"] == 1
        assert data["limit"] == 2

    def test_pagination_negative_skip(self, client, admin_token):
        resp = client.get(
            "/api/users?skip=-1",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422

    def test_pagination_zero_limit(self, client, admin_token):
        resp = client.get(
            "/api/users?limit=0",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422

    def test_pagination_limit_too_high(self, client, admin_token):
        resp = client.get(
            "/api/users?limit=200",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422

    def test_pagination_defaults(self, client, admin_token):
        resp = client.get(
            "/api/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["skip"] == 0
        assert data["limit"] == 20
        assert "total" in data
        assert isinstance(data["users"], list)
