from sqlalchemy import Column, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    active = Column(String, nullable=False, default="true")
    created_at = Column(String, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "active": self.active,
            "created_at": self.created_at,
        }


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", "tenant_id", name="uq_user_tenant_username"),
    )

    id = Column(String, primary_key=True)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, ForeignKey("roles.name"), nullable=False)
    name = Column(String, nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "password": self.password,
            "role": self.role,
            "name": self.name,
            "tenant_id": self.tenant_id,
        }


class Role(Base):
    __tablename__ = "roles"

    name = Column(String, primary_key=True)
    description = Column(String, nullable=False, default="")

    def to_dict(self) -> dict:
        return {"name": self.name, "description": self.description}
