from functools import lru_cache
from typing import Optional

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from config import settings
from models import Base, Role, Tenant, User
from repositories.base import RoleRepository, TenantRepository, UserRepository


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


def create_tables() -> None:
    Base.metadata.create_all(bind=get_engine())
