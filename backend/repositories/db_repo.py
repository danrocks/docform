from functools import lru_cache
from typing import Optional

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from config import settings
from models import (
    AnswersetMetadata,
    AuditLog,
    Base,
    Role,
    Tenant,
    TemplateSettings,
    User,
    Workgroup,
    WorkgroupTemplate,
    WorkgroupUser,
    Workitem,
)
from repositories.base import (
    AnswersetMetadataRepository,
    AuditLogRepository,
    RoleRepository,
    TemplateSettingsRepository,
    TenantRepository,
    UserRepository,
    WorkgroupRepository,
    WorkgroupTemplateRepository,
    WorkgroupUserRepository,
    WorkitemRepository,
)


@lru_cache(maxsize=1)
def get_engine(database_url: str = None):
    url = database_url or settings.DATABASE_URL
    eng = create_engine(url)
    if "sqlite" in str(eng.url):
        event.listen(eng, "connect", lambda c, _: c.execute("PRAGMA foreign_keys=ON"))
    return eng


def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


class DbUserRepository(UserRepository):
    def get_all(self, tenant_id: str = None) -> list[dict]:
        with get_session() as session:
            q = session.query(User)
            if tenant_id is not None:
                q = q.filter(User.tenant_id == tenant_id)
            return [u.to_dict() for u in q.all()]

    def get_by_id(self, user_id: str) -> Optional[dict]:
        with get_session() as session:
            user = session.get(User, user_id)
            return user.to_dict() if user else None

    def get_by_username(self, username: str, tenant_id: str = None) -> Optional[dict]:
        with get_session() as session:
            q = session.query(User).filter(User.username == username)
            if tenant_id is not None:
                q = q.filter(User.tenant_id == tenant_id)
            else:
                q = q.filter(User.tenant_id.is_(None))
            user = q.first()
            return user.to_dict() if user else None

    def create(self, user: dict) -> dict:
        with get_session() as session:
            db_user = User(**user)
            session.add(db_user)
            session.commit()
            session.refresh(db_user)
            return db_user.to_dict()

    def update(self, user_id: str, data: dict) -> Optional[dict]:
        with get_session() as session:
            user = session.get(User, user_id)
            if not user:
                return None
            for key, value in data.items():
                setattr(user, key, value)
            session.commit()
            session.refresh(user)
            return user.to_dict()

    def delete(self, user_id: str) -> bool:
        with get_session() as session:
            user = session.get(User, user_id)
            if not user:
                return False
            session.delete(user)
            session.commit()
            return True

    def count(self, tenant_id: str = None) -> int:
        with get_session() as session:
            q = session.query(User)
            if tenant_id is not None:
                q = q.filter(User.tenant_id == tenant_id)
            return q.count()

    def get_paginated(self, skip: int = 0, limit: int = 20, tenant_id: str = None) -> list[dict]:
        with get_session() as session:
            q = session.query(User).order_by(User.username)
            if tenant_id is not None:
                q = q.filter(User.tenant_id == tenant_id)
            users = q.offset(skip).limit(limit).all()
            return [u.to_dict() for u in users]


class DbRoleRepository(RoleRepository):
    def get_all(self) -> list[dict]:
        with get_session() as session:
            return [r.to_dict() for r in session.query(Role).all()]

    def get_by_name(self, name: str) -> Optional[dict]:
        with get_session() as session:
            role = session.get(Role, name)
            return role.to_dict() if role else None

    def create(self, role: dict) -> dict:
        with get_session() as session:
            db_role = Role(**role)
            session.add(db_role)
            session.commit()
            session.refresh(db_role)
            return db_role.to_dict()

    def update(self, name: str, data: dict) -> Optional[dict]:
        with get_session() as session:
            role = session.get(Role, name)
            if not role:
                return None
            for key, value in data.items():
                setattr(role, key, value)
            session.commit()
            session.refresh(role)
            return role.to_dict()

    def delete(self, name: str) -> bool:
        with get_session() as session:
            role = session.get(Role, name)
            if not role:
                return False
            session.delete(role)
            session.commit()
            return True

    def count(self) -> int:
        with get_session() as session:
            return session.query(Role).count()


class DbTenantRepository(TenantRepository):
    def get_all(self) -> list[dict]:
        with get_session() as session:
            return [t.to_dict() for t in session.query(Tenant).all()]

    def get_by_id(self, tenant_id: str) -> Optional[dict]:
        with get_session() as session:
            tenant = session.get(Tenant, tenant_id)
            return tenant.to_dict() if tenant else None

    def get_by_slug(self, slug: str) -> Optional[dict]:
        with get_session() as session:
            tenant = session.query(Tenant).filter(Tenant.slug == slug).first()
            return tenant.to_dict() if tenant else None

    def create(self, tenant: dict) -> dict:
        with get_session() as session:
            db_tenant = Tenant(**tenant)
            session.add(db_tenant)
            session.commit()
            session.refresh(db_tenant)
            return db_tenant.to_dict()

    def update(self, tenant_id: str, data: dict) -> Optional[dict]:
        with get_session() as session:
            tenant = session.get(Tenant, tenant_id)
            if not tenant:
                return None
            for key, value in data.items():
                setattr(tenant, key, value)
            session.commit()
            session.refresh(tenant)
            return tenant.to_dict()

    def delete(self, tenant_id: str) -> bool:
        with get_session() as session:
            tenant = session.get(Tenant, tenant_id)
            if not tenant:
                return False
            session.delete(tenant)
            session.commit()
            return True

    def count(self) -> int:
        with get_session() as session:
            return session.query(Tenant).count()


class DbWorkgroupRepository(WorkgroupRepository):
    def get_all(self, tenant_id: str = None) -> list[dict]:
        with get_session() as session:
            q = session.query(Workgroup)
            if tenant_id is not None:
                q = q.filter(Workgroup.tenant_id == tenant_id)
            return [w.to_dict() for w in q.order_by(Workgroup.name).all()]

    def get_by_id(self, workgroup_id: str) -> Optional[dict]:
        with get_session() as session:
            wg = session.get(Workgroup, workgroup_id)
            return wg.to_dict() if wg else None

    def create(self, workgroup: dict) -> dict:
        with get_session() as session:
            db_wg = Workgroup(**workgroup)
            session.add(db_wg)
            session.commit()
            session.refresh(db_wg)
            return db_wg.to_dict()

    def update(self, workgroup_id: str, data: dict) -> Optional[dict]:
        with get_session() as session:
            wg = session.get(Workgroup, workgroup_id)
            if not wg:
                return None
            for key, value in data.items():
                setattr(wg, key, value)
            session.commit()
            session.refresh(wg)
            return wg.to_dict()

    def delete(self, workgroup_id: str) -> bool:
        with get_session() as session:
            wg = session.get(Workgroup, workgroup_id)
            if not wg:
                return False
            session.delete(wg)
            session.commit()
            return True

    def count(self, tenant_id: str = None) -> int:
        with get_session() as session:
            q = session.query(Workgroup)
            if tenant_id is not None:
                q = q.filter(Workgroup.tenant_id == tenant_id)
            return q.count()

    def get_paginated(self, skip: int = 0, limit: int = 20, tenant_id: str = None) -> list[dict]:
        with get_session() as session:
            q = session.query(Workgroup).order_by(Workgroup.name)
            if tenant_id is not None:
                q = q.filter(Workgroup.tenant_id == tenant_id)
            return [w.to_dict() for w in q.offset(skip).limit(limit).all()]


class DbTemplateSettingsRepository(TemplateSettingsRepository):
    def get_by_template_id(self, template_id: str) -> Optional[dict]:
        with get_session() as session:
            ts = session.get(TemplateSettings, template_id)
            return ts.to_dict() if ts else None

    def create(self, settings_obj: dict) -> dict:
        with get_session() as session:
            db_ts = TemplateSettings(**settings_obj)
            session.add(db_ts)
            session.commit()
            session.refresh(db_ts)
            return db_ts.to_dict()

    def update(self, template_id: str, data: dict) -> Optional[dict]:
        with get_session() as session:
            ts = session.get(TemplateSettings, template_id)
            if not ts:
                return None
            for key, value in data.items():
                setattr(ts, key, value)
            session.commit()
            session.refresh(ts)
            return ts.to_dict()

    def delete(self, template_id: str) -> bool:
        with get_session() as session:
            ts = session.get(TemplateSettings, template_id)
            if not ts:
                return False
            session.delete(ts)
            session.commit()
            return True

    def get_restricted_templates(self, tenant_id: str = None) -> list[dict]:
        with get_session() as session:
            q = session.query(TemplateSettings).filter(
                TemplateSettings.restricted_to_workgroups.is_(True)
            )
            if tenant_id is not None:
                q = q.filter(TemplateSettings.tenant_id == tenant_id)
            return [ts.to_dict() for ts in q.all()]


class DbWorkgroupTemplateRepository(WorkgroupTemplateRepository):
    def add_template(self, workgroup_id: str, template_id: str) -> dict:
        with get_session() as session:
            existing = session.get(WorkgroupTemplate, (workgroup_id, template_id))
            if existing:
                return existing.to_dict()
            link = WorkgroupTemplate(workgroup_id=workgroup_id, template_id=template_id)
            session.add(link)
            session.commit()
            session.refresh(link)
            return link.to_dict()

    def remove_template(self, workgroup_id: str, template_id: str) -> bool:
        with get_session() as session:
            link = session.get(WorkgroupTemplate, (workgroup_id, template_id))
            if not link:
                return False
            session.delete(link)
            session.commit()
            return True

    def get_workgroup_templates(self, workgroup_id: str) -> list[dict]:
        with get_session() as session:
            rows = (
                session.query(WorkgroupTemplate)
                .filter(WorkgroupTemplate.workgroup_id == workgroup_id)
                .all()
            )
            return [r.to_dict() for r in rows]

    def get_template_workgroups(self, template_id: str) -> list[dict]:
        with get_session() as session:
            rows = (
                session.query(WorkgroupTemplate)
                .filter(WorkgroupTemplate.template_id == template_id)
                .all()
            )
            return [r.to_dict() for r in rows]


class DbWorkgroupUserRepository(WorkgroupUserRepository):
    def add_user(self, workgroup_id: str, user_id: str) -> dict:
        with get_session() as session:
            existing = session.get(WorkgroupUser, (workgroup_id, user_id))
            if existing:
                return existing.to_dict()
            link = WorkgroupUser(workgroup_id=workgroup_id, user_id=user_id)
            session.add(link)
            session.commit()
            session.refresh(link)
            return link.to_dict()

    def remove_user(self, workgroup_id: str, user_id: str) -> bool:
        with get_session() as session:
            link = session.get(WorkgroupUser, (workgroup_id, user_id))
            if not link:
                return False
            session.delete(link)
            session.commit()
            return True

    def get_workgroup_users(self, workgroup_id: str) -> list[dict]:
        with get_session() as session:
            rows = (
                session.query(WorkgroupUser)
                .filter(WorkgroupUser.workgroup_id == workgroup_id)
                .all()
            )
            return [r.to_dict() for r in rows]

    def get_user_workgroups(self, user_id: str) -> list[dict]:
        with get_session() as session:
            rows = (
                session.query(WorkgroupUser)
                .filter(WorkgroupUser.user_id == user_id)
                .all()
            )
            return [r.to_dict() for r in rows]


class DbWorkitemRepository(WorkitemRepository):
    def get_all(self, tenant_id: str = None) -> list[dict]:
        with get_session() as session:
            q = session.query(Workitem)
            if tenant_id is not None:
                q = q.filter(Workitem.tenant_id == tenant_id)
            return [w.to_dict() for w in q.all()]

    def get_by_id(self, workitem_id: str) -> Optional[dict]:
        with get_session() as session:
            wi = session.get(Workitem, workitem_id)
            return wi.to_dict() if wi else None

    def create(self, workitem: dict) -> dict:
        with get_session() as session:
            db_wi = Workitem(**workitem)
            session.add(db_wi)
            session.commit()
            session.refresh(db_wi)
            return db_wi.to_dict()

    def update(self, workitem_id: str, data: dict) -> Optional[dict]:
        with get_session() as session:
            wi = session.get(Workitem, workitem_id)
            if not wi:
                return None
            for key, value in data.items():
                setattr(wi, key, value)
            session.commit()
            session.refresh(wi)
            return wi.to_dict()

    def delete(self, workitem_id: str) -> bool:
        with get_session() as session:
            wi = session.get(Workitem, workitem_id)
            if not wi:
                return False
            session.delete(wi)
            session.commit()
            return True

    def count(self, tenant_id: str = None) -> int:
        with get_session() as session:
            q = session.query(Workitem)
            if tenant_id is not None:
                q = q.filter(Workitem.tenant_id == tenant_id)
            return q.count()

    def get_by_workgroup(self, workgroup_id: str) -> list[dict]:
        with get_session() as session:
            rows = (
                session.query(Workitem)
                .filter(Workitem.workgroup_id == workgroup_id)
                .all()
            )
            return [r.to_dict() for r in rows]

    def name_exists_in_workgroup(self, workgroup_id: str, name: str, exclude_id: str = None) -> bool:
        with get_session() as session:
            q = session.query(Workitem).filter(
                Workitem.workgroup_id == workgroup_id,
                Workitem.name == name,
            )
            if exclude_id:
                q = q.filter(Workitem.id != exclude_id)
            return q.first() is not None


class DbAnswersetMetadataRepository(AnswersetMetadataRepository):
    def get_all(self, tenant_id: str = None) -> list[dict]:
        with get_session() as session:
            q = session.query(AnswersetMetadata)
            if tenant_id is not None:
                q = q.filter(AnswersetMetadata.tenant_id == tenant_id)
            return [m.to_dict() for m in q.order_by(AnswersetMetadata.submitted_at.desc()).all()]

    def get_by_id(self, answerset_id: str) -> Optional[dict]:
        with get_session() as session:
            meta = session.get(AnswersetMetadata, answerset_id)
            return meta.to_dict() if meta else None

    def create(self, metadata: dict) -> dict:
        import json
        row_data = dict(metadata)
        if "shared_with" in row_data and isinstance(row_data["shared_with"], list):
            row_data["shared_with"] = json.dumps(row_data["shared_with"])
        if "details" in row_data and isinstance(row_data["details"], dict):
            row_data.pop("details", None)
        # Map interviewVersion key to column name
        if "interviewVersion" in row_data:
            row_data["interview_version"] = row_data.pop("interviewVersion")
        with get_session() as session:
            db_meta = AnswersetMetadata(**row_data)
            session.add(db_meta)
            session.commit()
            session.refresh(db_meta)
            return db_meta.to_dict()

    def update(self, answerset_id: str, data: dict) -> Optional[dict]:
        import json
        with get_session() as session:
            meta = session.get(AnswersetMetadata, answerset_id)
            if not meta:
                return None
            update_data = dict(data)
            if "shared_with" in update_data and isinstance(update_data["shared_with"], list):
                update_data["shared_with"] = json.dumps(update_data["shared_with"])
            if "interviewVersion" in update_data:
                update_data["interview_version"] = update_data.pop("interviewVersion")
            for key, value in update_data.items():
                if hasattr(meta, key):
                    setattr(meta, key, value)
            session.commit()
            session.refresh(meta)
            return meta.to_dict()

    def delete(self, answerset_id: str) -> bool:
        with get_session() as session:
            meta = session.get(AnswersetMetadata, answerset_id)
            if not meta:
                return False
            session.delete(meta)
            session.commit()
            return True

    def count(self, tenant_id: str = None, user_id: str = None, workgroup_ids: list = None, template_id: str = None) -> int:
        with get_session() as session:
            q = session.query(AnswersetMetadata)
            q = self._apply_filters(q, tenant_id, user_id, workgroup_ids, template_id)
            return q.count()

    def get_paginated(
        self, skip: int = 0, limit: int = 20, tenant_id: str = None,
        user_id: str = None, workgroup_ids: list = None,
        template_id: str = None,
    ) -> list[dict]:
        with get_session() as session:
            q = session.query(AnswersetMetadata)
            q = self._apply_filters(q, tenant_id, user_id, workgroup_ids, template_id)
            rows = q.order_by(AnswersetMetadata.submitted_at.desc()).offset(skip).limit(limit).all()
            return [m.to_dict() for m in rows]

    def get_by_workgroup(self, workgroup_id: str) -> list[dict]:
        with get_session() as session:
            rows = (
                session.query(AnswersetMetadata)
                .filter(AnswersetMetadata.workgroup_id == workgroup_id)
                .order_by(AnswersetMetadata.submitted_at.desc())
                .all()
            )
            return [m.to_dict() for m in rows]

    def get_shared_with_user(self, user_id: str) -> list[dict]:
        with get_session() as session:
            # Use LIKE for JSON array search since shared_with is stored as JSON text
            rows = (
                session.query(AnswersetMetadata)
                .filter(AnswersetMetadata.shared_with.like(f'%"{user_id}"%'))
                .all()
            )
            return [m.to_dict() for m in rows]

    def _apply_filters(self, q, tenant_id, user_id, workgroup_ids, template_id):
        from sqlalchemy import or_
        if tenant_id is not None:
            q = q.filter(AnswersetMetadata.tenant_id == tenant_id)
        if template_id is not None:
            q = q.filter(AnswersetMetadata.template_id == template_id)
        if user_id is not None:
            conditions = [AnswersetMetadata.submitted_by == user_id]
            conditions.append(AnswersetMetadata.shared_with.like(f'%"{user_id}"%'))
            if workgroup_ids:
                conditions.append(AnswersetMetadata.workgroup_id.in_(workgroup_ids))
            q = q.filter(or_(*conditions))
        return q


class DbAuditLogRepository(AuditLogRepository):
    def create(self, entry: dict) -> dict:
        import json
        row_data = dict(entry)
        if "details" in row_data and isinstance(row_data["details"], dict):
            row_data["details"] = json.dumps(row_data["details"])
        with get_session() as session:
            db_entry = AuditLog(**row_data)
            session.add(db_entry)
            session.commit()
            session.refresh(db_entry)
            return db_entry.to_dict()

    def get_by_answerset(self, answerset_id: str) -> list[dict]:
        with get_session() as session:
            rows = (
                session.query(AuditLog)
                .filter(AuditLog.answerset_id == answerset_id)
                .order_by(AuditLog.timestamp.desc())
                .all()
            )
            return [r.to_dict() for r in rows]

    def get_all(self, tenant_id: str = None, skip: int = 0, limit: int = 50) -> list[dict]:
        with get_session() as session:
            q = session.query(AuditLog)
            if tenant_id is not None:
                q = q.filter(AuditLog.tenant_id == tenant_id)
            rows = q.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
            return [r.to_dict() for r in rows]

    def count(self, tenant_id: str = None) -> int:
        with get_session() as session:
            q = session.query(AuditLog)
            if tenant_id is not None:
                q = q.filter(AuditLog.tenant_id == tenant_id)
            return q.count()


def create_tables() -> None:
    Base.metadata.create_all(bind=get_engine())
