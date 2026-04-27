from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import settings
from models import Base, Role, User
from repositories.base import RoleRepository, UserRepository

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


class DbUserRepository(UserRepository):
    def get_all(self) -> list[dict]:
        with SessionLocal() as session:
            users = session.query(User).all()
            return [u.to_dict() for u in users]

    def get_by_id(self, user_id: str) -> Optional[dict]:
        with SessionLocal() as session:
            user = session.get(User, user_id)
            return user.to_dict() if user else None

    def get_by_username(self, username: str) -> Optional[dict]:
        with SessionLocal() as session:
            user = session.query(User).filter(User.username == username).first()
            return user.to_dict() if user else None

    def create(self, user: dict) -> dict:
        with SessionLocal() as session:
            db_user = User(**user)
            session.add(db_user)
            session.commit()
            session.refresh(db_user)
            return db_user.to_dict()

    def update(self, user_id: str, data: dict) -> Optional[dict]:
        with SessionLocal() as session:
            user = session.get(User, user_id)
            if not user:
                return None
            for key, value in data.items():
                setattr(user, key, value)
            session.commit()
            session.refresh(user)
            return user.to_dict()

    def delete(self, user_id: str) -> bool:
        with SessionLocal() as session:
            user = session.get(User, user_id)
            if not user:
                return False
            session.delete(user)
            session.commit()
            return True

    def count(self) -> int:
        with SessionLocal() as session:
            return session.query(User).count()


class DbRoleRepository(RoleRepository):
    def get_all(self) -> list[dict]:
        with SessionLocal() as session:
            return [r.to_dict() for r in session.query(Role).all()]

    def get_by_name(self, name: str) -> Optional[dict]:
        with SessionLocal() as session:
            role = session.get(Role, name)
            return role.to_dict() if role else None

    def create(self, role: dict) -> dict:
        with SessionLocal() as session:
            db_role = Role(**role)
            session.add(db_role)
            session.commit()
            session.refresh(db_role)
            return db_role.to_dict()

    def delete(self, name: str) -> bool:
        with SessionLocal() as session:
            role = session.get(Role, name)
            if not role:
                return False
            session.delete(role)
            session.commit()
            return True

    def count(self) -> int:
        with SessionLocal() as session:
            return session.query(Role).count()


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
