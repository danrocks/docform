from sqlalchemy import Boolean, Column, String, ForeignKey, UniqueConstraint
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


class Workgroup(Base):
    __tablename__ = "workgroups"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False, default="")
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    requires_approval = Column(Boolean, nullable=False, default=False)
    created_at = Column(String, nullable=False)
    created_by = Column(String, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tenant_id": self.tenant_id,
            "requires_approval": bool(self.requires_approval),
            "created_at": self.created_at,
            "created_by": self.created_by,
        }


class TemplateSettings(Base):
    __tablename__ = "template_settings"

    template_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    restricted_to_workgroups = Column(Boolean, nullable=False, default=False)
    created_at = Column(String, nullable=False)
    created_by = Column(String, nullable=False)

    def to_dict(self) -> dict:
        return {
            "template_id": self.template_id,
            "tenant_id": self.tenant_id,
            "restricted_to_workgroups": bool(self.restricted_to_workgroups),
            "created_at": self.created_at,
            "created_by": self.created_by,
        }


class WorkgroupTemplate(Base):
    __tablename__ = "workgroup_templates"

    workgroup_id = Column(
        String,
        ForeignKey("workgroups.id", ondelete="CASCADE"),
        primary_key=True,
    )
    template_id = Column(
        String,
        ForeignKey("template_settings.template_id", ondelete="CASCADE"),
        primary_key=True,
    )

    def to_dict(self) -> dict:
        return {
            "workgroup_id": self.workgroup_id,
            "template_id": self.template_id,
        }


class Workitem(Base):
    __tablename__ = "workitems"
    __table_args__ = (
        UniqueConstraint("workgroup_id", "name", name="uq_workitem_workgroup_name"),
    )

    id = Column(String, primary_key=True)
    workgroup_id = Column(String, ForeignKey("workgroups.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False, default="")
    status = Column(String, nullable=False, default="draft")
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    created_at = Column(String, nullable=False)
    created_by = Column(String, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "workgroup_id": self.workgroup_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at,
            "created_by": self.created_by,
        }


class WorkgroupUser(Base):
    __tablename__ = "workgroup_users"

    workgroup_id = Column(
        String,
        ForeignKey("workgroups.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id = Column(
        String,
        ForeignKey("users.id"),
        primary_key=True,
    )

    def to_dict(self) -> dict:
        return {
            "workgroup_id": self.workgroup_id,
            "user_id": self.user_id,
        }
