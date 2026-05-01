import json
from pathlib import Path
from typing import Optional

from repositories.base import RoleRepository, TenantRepository, UserRepository

USERS_FILE = Path("data/users.json")
ROLES_FILE = Path("data/roles.json")
TENANTS_FILE = Path("data/tenants.json")


class JsonUserRepository(UserRepository):
    def _read(self) -> list[dict]:
        if not USERS_FILE.exists():
            return []
        return json.loads(USERS_FILE.read_text())

    def _write(self, users: list[dict]) -> None:
        USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        USERS_FILE.write_text(json.dumps(users, indent=2))

    def get_all(self, tenant_id: str = None) -> list[dict]:
        users = self._read()
        if tenant_id is not None:
            users = [u for u in users if u.get("tenant_id") == tenant_id]
        return users

    def get_by_id(self, user_id: str) -> Optional[dict]:
        return next((u for u in self._read() if u["id"] == user_id), None)

    def get_by_username(self, username: str, tenant_id: str = None) -> Optional[dict]:
        for u in self._read():
            if u["username"] == username:
                if tenant_id is not None:
                    if u.get("tenant_id") == tenant_id:
                        return u
                else:
                    if u.get("tenant_id") is None:
                        return u
        return None

    def create(self, user: dict) -> dict:
        users = self._read()
        users.append(user)
        self._write(users)
        return user

    def update(self, user_id: str, data: dict) -> Optional[dict]:
        users = self._read()
        for i, u in enumerate(users):
            if u["id"] == user_id:
                users[i].update(data)
                self._write(users)
                return users[i]
        return None

    def delete(self, user_id: str) -> bool:
        users = self._read()
        new_users = [u for u in users if u["id"] != user_id]
        if len(new_users) == len(users):
            return False
        self._write(new_users)
        return True

    def count(self, tenant_id: str = None) -> int:
        users = self._read()
        if tenant_id is not None:
            users = [u for u in users if u.get("tenant_id") == tenant_id]
        return len(users)

    def get_paginated(self, skip: int = 0, limit: int = 20, tenant_id: str = None) -> list[dict]:
        users = self._read()
        if tenant_id is not None:
            users = [u for u in users if u.get("tenant_id") == tenant_id]
        return users[skip:skip + limit]


class JsonRoleRepository(RoleRepository):
    def _read(self) -> list[dict]:
        if not ROLES_FILE.exists():
            return []
        return json.loads(ROLES_FILE.read_text())

    def _write(self, roles: list[dict]) -> None:
        ROLES_FILE.parent.mkdir(parents=True, exist_ok=True)
        ROLES_FILE.write_text(json.dumps(roles, indent=2))

    def get_all(self) -> list[dict]:
        return self._read()

    def get_by_name(self, name: str) -> Optional[dict]:
        return next((r for r in self._read() if r["name"] == name), None)

    def create(self, role: dict) -> dict:
        roles = self._read()
        roles.append(role)
        self._write(roles)
        return role

    def update(self, name: str, data: dict) -> Optional[dict]:
        roles = self._read()
        for i, r in enumerate(roles):
            if r["name"] == name:
                roles[i].update(data)
                self._write(roles)
                return roles[i]
        return None

    def delete(self, name: str) -> bool:
        roles = self._read()
        new_roles = [r for r in roles if r["name"] != name]
        if len(new_roles) == len(roles):
            return False
        self._write(new_roles)
        return True

    def count(self) -> int:
        return len(self._read())


class JsonTenantRepository(TenantRepository):
    def _read(self) -> list[dict]:
        if not TENANTS_FILE.exists():
            return []
        return json.loads(TENANTS_FILE.read_text())

    def _write(self, tenants: list[dict]) -> None:
        TENANTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        TENANTS_FILE.write_text(json.dumps(tenants, indent=2))

    def get_all(self) -> list[dict]:
        return self._read()

    def get_by_id(self, tenant_id: str) -> Optional[dict]:
        return next((t for t in self._read() if t["id"] == tenant_id), None)

    def get_by_slug(self, slug: str) -> Optional[dict]:
        return next((t for t in self._read() if t["slug"] == slug), None)

    def create(self, tenant: dict) -> dict:
        tenants = self._read()
        tenants.append(tenant)
        self._write(tenants)
        return tenant

    def update(self, tenant_id: str, data: dict) -> Optional[dict]:
        tenants = self._read()
        for i, t in enumerate(tenants):
            if t["id"] == tenant_id:
                tenants[i].update(data)
                self._write(tenants)
                return tenants[i]
        return None

    def delete(self, tenant_id: str) -> bool:
        tenants = self._read()
        new_tenants = [t for t in tenants if t["id"] != tenant_id]
        if len(new_tenants) == len(tenants):
            return False
        self._write(new_tenants)
        return True

    def count(self) -> int:
        return len(self._read())
