from abc import ABC, abstractmethod
from typing import Optional


class UserRepository(ABC):
    @abstractmethod
    def get_all(self, tenant_id: str = None) -> list[dict]: ...

    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[dict]: ...

    @abstractmethod
    def get_by_username(self, username: str, tenant_id: str = None) -> Optional[dict]: ...

    @abstractmethod
    def create(self, user: dict) -> dict: ...

    @abstractmethod
    def update(self, user_id: str, data: dict) -> Optional[dict]: ...

    @abstractmethod
    def delete(self, user_id: str) -> bool: ...

    @abstractmethod
    def count(self, tenant_id: str = None) -> int: ...

    @abstractmethod
    def get_paginated(self, skip: int = 0, limit: int = 20, tenant_id: str = None) -> list[dict]: ...


class RoleRepository(ABC):
    @abstractmethod
    def get_all(self) -> list[dict]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[dict]: ...

    @abstractmethod
    def create(self, role: dict) -> dict: ...

    @abstractmethod
    def update(self, name: str, data: dict) -> Optional[dict]: ...

    @abstractmethod
    def delete(self, name: str) -> bool: ...

    @abstractmethod
    def count(self) -> int: ...


class TenantRepository(ABC):
    @abstractmethod
    def get_all(self) -> list[dict]: ...

    @abstractmethod
    def get_by_id(self, tenant_id: str) -> Optional[dict]: ...

    @abstractmethod
    def get_by_slug(self, slug: str) -> Optional[dict]: ...

    @abstractmethod
    def create(self, tenant: dict) -> dict: ...

    @abstractmethod
    def update(self, tenant_id: str, data: dict) -> Optional[dict]: ...

    @abstractmethod
    def delete(self, tenant_id: str) -> bool: ...

    @abstractmethod
    def count(self) -> int: ...
