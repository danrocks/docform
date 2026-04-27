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

    import repositories.json_repo as jr
    monkeypatch.setattr(jr, "ROLES_FILE", roles_file)
    monkeypatch.setattr(jr, "USERS_FILE", users_file)

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
def seeded_roles(role_repo):
    role_repo.create({"name": "admin", "description": "Administrator"})
    role_repo.create({"name": "staff", "description": "Staff member"})
    role_repo.create({"name": "approver", "description": "Approver"})
    return role_repo


@pytest.fixture
def client(seeded_roles):
    from fastapi.testclient import TestClient
    from main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_token(client, user_repo):
    from auth_utils import hash_password
    user_repo.create({
        "id": "test-admin-1",
        "username": "testadmin",
        "password": hash_password("pass123"),
        "role": "admin",
        "name": "Test Admin",
    })
    resp = client.post("/api/auth/login", data={"username": "testadmin", "password": "pass123"})
    return resp.json()["access_token"]


@pytest.fixture
def staff_token(client, user_repo):
    from auth_utils import hash_password
    user_repo.create({
        "id": "test-staff-1",
        "username": "teststaff",
        "password": hash_password("pass123"),
        "role": "staff",
        "name": "Test Staff",
    })
    resp = client.post("/api/auth/login", data={"username": "teststaff", "password": "pass123"})
    return resp.json()["access_token"]
