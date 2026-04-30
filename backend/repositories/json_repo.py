import json
from pathlib import Path
from typing import Optional

from repositories.base import RoleRepository, UserRepository

USERS_FILE = Path("data/users.json")
ROLES_FILE = Path("data/roles.json")


class JsonUserRepository(UserRepository):
    def _read(self) -> list[dict]:
        if not USERS_FILE.exists():
            return []
        return json.loads(USERS_FILE.read_text())

    def _write(self, users: list[dict]) -> None:
        USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        USERS_FILE.write_text(json.dumps(users, indent=2))

    def get_all(self) -> list[dict]:
        return self._read()

    def get_by_id(self, user_id: str) -> Optional[dict]:
        return next((u for u in self._read() if u["id"] == user_id), None)

    def get_by_username(self, username: str) -> Optional[dict]:
        return next((u for u in self._read() if u["username"] == username), None)

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

    def count(self) -> int:
        return len(self._read())


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
