from abc import ABC, abstractmethod
from typing import Optional


class UserRepository(ABC):
    @abstractmethod
    def get_all(self) -> list[dict]: ...

    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[dict]: ...

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[dict]: ...

    @abstractmethod
    def create(self, user: dict) -> dict: ...

    @abstractmethod
    def update(self, user_id: str, data: dict) -> Optional[dict]: ...

    @abstractmethod
    def delete(self, user_id: str) -> bool: ...

    @abstractmethod
    def count(self) -> int: ...


class RoleRepository(ABC):
    @abstractmethod
    def get_all(self) -> list[dict]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[dict]: ...

    @abstractmethod
    def create(self, role: dict) -> dict: ...

    @abstractmethod
    def delete(self, name: str) -> bool: ...

    @abstractmethod
    def count(self) -> int: ...
