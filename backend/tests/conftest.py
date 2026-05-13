import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Use JSON backend for tests to avoid needing a database
os.environ["STORAGE_BACKEND"] = "json"
os.environ["OPENAI_API_KEY"] = "test"
os.environ["GEMINI_KEY"] = "test"
os.environ["DEVIN_KEY"] = "test"


@pytest.fixture(autouse=True)
def tmp_data_dir(tmp_path, monkeypatch):
    """Redirect JSON repo files to a temp directory for test isolation."""
    roles_file = tmp_path / "roles.json"
    users_file = tmp_path / "users.json"
    tenants_file = tmp_path / "tenants.json"
    workgroups_file = tmp_path / "workgroups.json"
    template_settings_file = tmp_path / "template_settings.json"
    workgroup_templates_file = tmp_path / "workgroup_templates.json"
    workgroup_users_file = tmp_path / "workgroup_users.json"

    import repositories.json_repo as jr
    monkeypatch.setattr(jr, "ROLES_FILE", roles_file)
    monkeypatch.setattr(jr, "USERS_FILE", users_file)
    monkeypatch.setattr(jr, "TENANTS_FILE", tenants_file)
    monkeypatch.setattr(jr, "WORKGROUPS_FILE", workgroups_file)
    monkeypatch.setattr(jr, "TEMPLATE_SETTINGS_FILE", template_settings_file)
    monkeypatch.setattr(jr, "WORKGROUP_TEMPLATES_FILE", workgroup_templates_file)
    monkeypatch.setattr(jr, "WORKGROUP_USERS_FILE", workgroup_users_file)

    import rate_limit
    rate_limit._attempts.clear()

    import auth_utils
    auth_utils._revoked_jtis.clear()

    return tmp_path


@pytest.fixture
def role_repo():
    from repositories.factory import get_role_repository
    return get_role_repository()


@pytest.fixture
def user_repo():
    from repositories.factory import get_user_repository
    return get_user_repository()


@pytest.fixture
def tenant_repo():
    from repositories.factory import get_tenant_repository
    return get_tenant_repository()


@pytest.fixture
def seeded_roles(role_repo):
    role_repo.create({"name": "admin", "description": "Administrator"})
    role_repo.create({"name": "staff", "description": "Staff member"})
    role_repo.create({"name": "approver", "description": "Approver"})
    role_repo.create({"name": "superadmin", "description": "Super administrator - manages tenants"})
    return role_repo


@pytest.fixture
def tenant_a(tenant_repo):
    return tenant_repo.create({
        "id": "tenant-a",
        "name": "Alpha Corp",
        "slug": "alpha",
        "active": "true",
        "created_at": "2026-01-01T00:00:00",
    })


@pytest.fixture
def tenant_b(tenant_repo):
    return tenant_repo.create({
        "id": "tenant-b",
        "name": "Beta Inc",
        "slug": "beta",
        "active": "true",
        "created_at": "2026-01-01T00:00:00",
    })


@pytest.fixture
def client(seeded_roles):
    from fastapi.testclient import TestClient
    from main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_token(client, user_repo, tenant_a):
    """Admin token for tenant A (alpha subdomain)."""
    from auth_utils import hash_password
    user_repo.create({
        "id": "test-admin-1",
        "username": "testadmin",
        "password": hash_password("pass1234"),
        "role": "admin",
        "name": "Test Admin",
        "tenant_id": "tenant-a",
    })
    resp = client.post(
        "/api/auth/login",
        data={"username": "testadmin", "password": "pass1234"},
        headers={"Host": "alpha.localhost:3000"},
    )
    return resp.json()["access_token"]


@pytest.fixture
def staff_token(client, user_repo, tenant_a):
    """Staff token for tenant A (alpha subdomain)."""
    from auth_utils import hash_password
    user_repo.create({
        "id": "test-staff-1",
        "username": "teststaff",
        "password": hash_password("pass1234"),
        "role": "staff",
        "name": "Test Staff",
        "tenant_id": "tenant-a",
    })
    resp = client.post(
        "/api/auth/login",
        data={"username": "teststaff", "password": "pass1234"},
        headers={"Host": "alpha.localhost:3000"},
    )
    return resp.json()["access_token"]


@pytest.fixture
def admin_token_tenant_b(client, user_repo, tenant_b):
    """Admin token for tenant B (beta subdomain)."""
    from auth_utils import hash_password
    user_repo.create({
        "id": "test-admin-b",
        "username": "testadmin",
        "password": hash_password("pass1234"),
        "role": "admin",
        "name": "Test Admin B",
        "tenant_id": "tenant-b",
    })
    resp = client.post(
        "/api/auth/login",
        data={"username": "testadmin", "password": "pass1234"},
        headers={"Host": "beta.localhost:3000"},
    )
    return resp.json()["access_token"]


@pytest.fixture
def superadmin_token(client, user_repo):
    """Superadmin token (admin subdomain, tenant_id=None)."""
    from auth_utils import hash_password
    user_repo.create({
        "id": "test-superadmin",
        "username": "testsuperadmin",
        "password": hash_password("pass1234"),
        "role": "superadmin",
        "name": "Super Admin",
        "tenant_id": None,
    })
    resp = client.post(
        "/api/auth/login",
        data={"username": "testsuperadmin", "password": "pass1234"},
        headers={"Host": "admin.localhost:3000"},
    )
    return resp.json()["access_token"]


def tenant_headers(slug, token):
    return {"Host": f"{slug}.localhost:3000", "Authorization": f"Bearer {token}"}


def admin_headers(token):
    return {"Host": "admin.localhost:3000", "Authorization": f"Bearer {token}"}
