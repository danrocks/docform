import json
from pathlib import Path
from typing import Optional

from repositories.base import UserRepository

USERS_FILE = Path("data/users.json")


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
