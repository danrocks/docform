import json
from pathlib import Path
from typing import Optional

from repositories.base import (
    RoleRepository,
    TemplateSettingsRepository,
    TenantRepository,
    UserRepository,
    WorkgroupRepository,
    WorkgroupTemplateRepository,
    WorkgroupUserRepository,
    WorkitemRepository,
)

USERS_FILE = Path("data/users.json")
ROLES_FILE = Path("data/roles.json")
TENANTS_FILE = Path("data/tenants.json")
WORKGROUPS_FILE = Path("data/workgroups.json")
TEMPLATE_SETTINGS_FILE = Path("data/template_settings.json")
WORKGROUP_TEMPLATES_FILE = Path("data/workgroup_templates.json")
WORKGROUP_USERS_FILE = Path("data/workgroup_users.json")
WORKITEMS_FILE = Path("data/workitems.json")


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


class JsonWorkgroupRepository(WorkgroupRepository):
    def _read(self) -> list[dict]:
        if not WORKGROUPS_FILE.exists():
            return []
        return json.loads(WORKGROUPS_FILE.read_text())

    def _write(self, items: list[dict]) -> None:
        WORKGROUPS_FILE.parent.mkdir(parents=True, exist_ok=True)
        WORKGROUPS_FILE.write_text(json.dumps(items, indent=2))

    def get_all(self, tenant_id: str = None) -> list[dict]:
        items = self._read()
        if tenant_id is not None:
            items = [w for w in items if w.get("tenant_id") == tenant_id]
        return sorted(items, key=lambda w: w.get("name", ""))

    def get_by_id(self, workgroup_id: str) -> Optional[dict]:
        return next((w for w in self._read() if w["id"] == workgroup_id), None)

    def create(self, workgroup: dict) -> dict:
        items = self._read()
        items.append(workgroup)
        self._write(items)
        return workgroup

    def update(self, workgroup_id: str, data: dict) -> Optional[dict]:
        items = self._read()
        for i, w in enumerate(items):
            if w["id"] == workgroup_id:
                items[i].update(data)
                self._write(items)
                return items[i]
        return None

    def delete(self, workgroup_id: str) -> bool:
        items = self._read()
        new_items = [w for w in items if w["id"] != workgroup_id]
        if len(new_items) == len(items):
            return False
        self._write(new_items)

        # CASCADE: remove workgroup_templates and workgroup_users entries
        wt_repo = JsonWorkgroupTemplateRepository()
        wt_items = wt_repo._read()
        wt_repo._write([r for r in wt_items if r.get("workgroup_id") != workgroup_id])

        wu_repo = JsonWorkgroupUserRepository()
        wu_items = wu_repo._read()
        wu_repo._write([r for r in wu_items if r.get("workgroup_id") != workgroup_id])

        wi_repo = JsonWorkitemRepository()
        wi_items = wi_repo._read()
        wi_repo._write([r for r in wi_items if r.get("workgroup_id") != workgroup_id])
        return True

    def count(self, tenant_id: str = None) -> int:
        items = self._read()
        if tenant_id is not None:
            items = [w for w in items if w.get("tenant_id") == tenant_id]
        return len(items)

    def get_paginated(self, skip: int = 0, limit: int = 20, tenant_id: str = None) -> list[dict]:
        items = self.get_all(tenant_id=tenant_id)
        return items[skip:skip + limit]


class JsonTemplateSettingsRepository(TemplateSettingsRepository):
    def _read(self) -> list[dict]:
        if not TEMPLATE_SETTINGS_FILE.exists():
            return []
        return json.loads(TEMPLATE_SETTINGS_FILE.read_text())

    def _write(self, items: list[dict]) -> None:
        TEMPLATE_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        TEMPLATE_SETTINGS_FILE.write_text(json.dumps(items, indent=2))

    def get_by_template_id(self, template_id: str) -> Optional[dict]:
        return next((s for s in self._read() if s["template_id"] == template_id), None)

    def create(self, settings: dict) -> dict:
        items = self._read()
        items.append(settings)
        self._write(items)
        return settings

    def update(self, template_id: str, data: dict) -> Optional[dict]:
        items = self._read()
        for i, s in enumerate(items):
            if s["template_id"] == template_id:
                items[i].update(data)
                self._write(items)
                return items[i]
        return None

    def delete(self, template_id: str) -> bool:
        items = self._read()
        new_items = [s for s in items if s["template_id"] != template_id]
        if len(new_items) == len(items):
            return False
        self._write(new_items)

        # CASCADE: remove workgroup_templates entries for this template
        wt_repo = JsonWorkgroupTemplateRepository()
        wt_items = wt_repo._read()
        wt_repo._write([r for r in wt_items if r.get("template_id") != template_id])
        return True

    def get_restricted_templates(self, tenant_id: str = None) -> list[dict]:
        items = [s for s in self._read() if s.get("restricted_to_workgroups")]
        if tenant_id is not None:
            items = [s for s in items if s.get("tenant_id") == tenant_id]
        return items


class JsonWorkgroupTemplateRepository(WorkgroupTemplateRepository):
    def _read(self) -> list[dict]:
        if not WORKGROUP_TEMPLATES_FILE.exists():
            return []
        return json.loads(WORKGROUP_TEMPLATES_FILE.read_text())

    def _write(self, items: list[dict]) -> None:
        WORKGROUP_TEMPLATES_FILE.parent.mkdir(parents=True, exist_ok=True)
        WORKGROUP_TEMPLATES_FILE.write_text(json.dumps(items, indent=2))

    def add_template(self, workgroup_id: str, template_id: str) -> dict:
        items = self._read()
        for r in items:
            if r["workgroup_id"] == workgroup_id and r["template_id"] == template_id:
                return r
        entry = {"workgroup_id": workgroup_id, "template_id": template_id}
        items.append(entry)
        self._write(items)
        return entry

    def remove_template(self, workgroup_id: str, template_id: str) -> bool:
        items = self._read()
        new_items = [
            r for r in items
            if not (r["workgroup_id"] == workgroup_id and r["template_id"] == template_id)
        ]
        if len(new_items) == len(items):
            return False
        self._write(new_items)
        return True

    def get_workgroup_templates(self, workgroup_id: str) -> list[dict]:
        return [r for r in self._read() if r["workgroup_id"] == workgroup_id]

    def get_template_workgroups(self, template_id: str) -> list[dict]:
        return [r for r in self._read() if r["template_id"] == template_id]


class JsonWorkgroupUserRepository(WorkgroupUserRepository):
    def _read(self) -> list[dict]:
        if not WORKGROUP_USERS_FILE.exists():
            return []
        return json.loads(WORKGROUP_USERS_FILE.read_text())

    def _write(self, items: list[dict]) -> None:
        WORKGROUP_USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        WORKGROUP_USERS_FILE.write_text(json.dumps(items, indent=2))

    def add_user(self, workgroup_id: str, user_id: str) -> dict:
        items = self._read()
        for r in items:
            if r["workgroup_id"] == workgroup_id and r["user_id"] == user_id:
                return r
        entry = {"workgroup_id": workgroup_id, "user_id": user_id}
        items.append(entry)
        self._write(items)
        return entry

    def remove_user(self, workgroup_id: str, user_id: str) -> bool:
        items = self._read()
        new_items = [
            r for r in items
            if not (r["workgroup_id"] == workgroup_id and r["user_id"] == user_id)
        ]
        if len(new_items) == len(items):
            return False
        self._write(new_items)
        return True

    def get_workgroup_users(self, workgroup_id: str) -> list[dict]:
        return [r for r in self._read() if r["workgroup_id"] == workgroup_id]

    def get_user_workgroups(self, user_id: str) -> list[dict]:
        return [r for r in self._read() if r["user_id"] == user_id]


class JsonWorkitemRepository(WorkitemRepository):
    def _read(self) -> list[dict]:
        if not WORKITEMS_FILE.exists():
            return []
        return json.loads(WORKITEMS_FILE.read_text())

    def _write(self, items: list[dict]) -> None:
        WORKITEMS_FILE.parent.mkdir(parents=True, exist_ok=True)
        WORKITEMS_FILE.write_text(json.dumps(items, indent=2))

    def get_all(self, tenant_id: str = None) -> list[dict]:
        items = self._read()
        if tenant_id is not None:
            items = [w for w in items if w.get("tenant_id") == tenant_id]
        return items

    def get_by_id(self, workitem_id: str) -> Optional[dict]:
        return next((w for w in self._read() if w["id"] == workitem_id), None)

    def create(self, workitem: dict) -> dict:
        items = self._read()
        items.append(workitem)
        self._write(items)
        return workitem

    def update(self, workitem_id: str, data: dict) -> Optional[dict]:
        items = self._read()
        for i, w in enumerate(items):
            if w["id"] == workitem_id:
                items[i].update(data)
                self._write(items)
                return items[i]
        return None

    def delete(self, workitem_id: str) -> bool:
        items = self._read()
        new_items = [w for w in items if w["id"] != workitem_id]
        if len(new_items) == len(items):
            return False
        self._write(new_items)
        return True

    def count(self, tenant_id: str = None) -> int:
        items = self._read()
        if tenant_id is not None:
            items = [w for w in items if w.get("tenant_id") == tenant_id]
        return len(items)

    def get_by_workgroup(self, workgroup_id: str) -> list[dict]:
        return [w for w in self._read() if w.get("workgroup_id") == workgroup_id]

    def name_exists_in_workgroup(self, workgroup_id: str, name: str, exclude_id: str = None) -> bool:
        for w in self._read():
            if w.get("workgroup_id") == workgroup_id and w.get("name") == name:
                if exclude_id and w["id"] == exclude_id:
                    continue
                return True
        return False
