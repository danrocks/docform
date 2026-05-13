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


class WorkgroupRepository(ABC):
    @abstractmethod
    def get_all(self, tenant_id: str = None) -> list[dict]: ...

    @abstractmethod
    def get_by_id(self, workgroup_id: str) -> Optional[dict]: ...

    @abstractmethod
    def create(self, workgroup: dict) -> dict: ...

    @abstractmethod
    def update(self, workgroup_id: str, data: dict) -> Optional[dict]: ...

    @abstractmethod
    def delete(self, workgroup_id: str) -> bool: ...

    @abstractmethod
    def count(self, tenant_id: str = None) -> int: ...

    @abstractmethod
    def get_paginated(self, skip: int = 0, limit: int = 20, tenant_id: str = None) -> list[dict]: ...


class TemplateSettingsRepository(ABC):
    @abstractmethod
    def get_by_template_id(self, template_id: str) -> Optional[dict]: ...

    @abstractmethod
    def create(self, settings: dict) -> dict: ...

    @abstractmethod
    def update(self, template_id: str, data: dict) -> Optional[dict]: ...

    @abstractmethod
    def delete(self, template_id: str) -> bool: ...

    @abstractmethod
    def get_restricted_templates(self, tenant_id: str = None) -> list[dict]: ...


class WorkgroupTemplateRepository(ABC):
    @abstractmethod
    def add_template(self, workgroup_id: str, template_id: str) -> dict: ...

    @abstractmethod
    def remove_template(self, workgroup_id: str, template_id: str) -> bool: ...

    @abstractmethod
    def get_workgroup_templates(self, workgroup_id: str) -> list[dict]: ...

    @abstractmethod
    def get_template_workgroups(self, template_id: str) -> list[dict]: ...


class WorkgroupUserRepository(ABC):
    @abstractmethod
    def add_user(self, workgroup_id: str, user_id: str) -> dict: ...

    @abstractmethod
    def remove_user(self, workgroup_id: str, user_id: str) -> bool: ...

    @abstractmethod
    def get_workgroup_users(self, workgroup_id: str) -> list[dict]: ...

    @abstractmethod
    def get_user_workgroups(self, user_id: str) -> list[dict]: ...


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
