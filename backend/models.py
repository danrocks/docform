from sqlalchemy import Boolean, Column, Integer, String, Text, ForeignKey, UniqueConstraint
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


class AnswersetMetadata(Base):
    __tablename__ = "answerset_metadata"

    id = Column(String, primary_key=True)
    template_id = Column(String, nullable=False, index=True)
    template_name = Column(String, nullable=False, default="")
    interview_version = Column(String, nullable=True)
    context = Column(Text, nullable=False, default="")
    workgroup_id = Column(String, ForeignKey("workgroups.id", ondelete="SET NULL"), nullable=True, index=True)
    submitted_by = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    submitted_by_name = Column(String, nullable=False, default="")
    submitted_at = Column(String, nullable=False)
    docx_path = Column(String, nullable=True)
    pdf_path = Column(String, nullable=True)
    shared_with = Column(Text, nullable=False, default="[]")  # JSON array of user IDs
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True, index=True)
    version = Column(Integer, nullable=False, default=1)
    status = Column(String, nullable=False, default="pending")

    def to_dict(self) -> dict:
        import json
        shared = self.shared_with or "[]"
        try:
            shared_list = json.loads(shared)
        except (json.JSONDecodeError, TypeError):
            shared_list = []
        return {
            "id": self.id,
            "template_id": self.template_id,
            "template_name": self.template_name,
            "interviewVersion": self.interview_version,
            "context": self.context,
            "workgroup_id": self.workgroup_id,
            "submitted_by": self.submitted_by,
            "submitted_by_name": self.submitted_by_name,
            "submitted_at": self.submitted_at,
            "docx_path": self.docx_path,
            "pdf_path": self.pdf_path,
            "shared_with": shared_list,
            "tenant_id": self.tenant_id,
            "version": self.version,
            "status": self.status,
        }


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(String, primary_key=True)
    answerset_id = Column(String, nullable=False, index=True)
    operation = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    user_name = Column(String, nullable=False, default="")
    tenant_id = Column(String, nullable=True, index=True)
    ip_address = Column(String, nullable=False, default="")
    timestamp = Column(String, nullable=False)
    details = Column(Text, nullable=False, default="{}")  # JSON object

    def to_dict(self) -> dict:
        import json
        try:
            details_dict = json.loads(self.details or "{}")
        except (json.JSONDecodeError, TypeError):
            details_dict = {}
        return {
            "id": self.id,
            "answerset_id": self.answerset_id,
            "operation": self.operation,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "tenant_id": self.tenant_id,
            "ip_address": self.ip_address,
            "timestamp": self.timestamp,
            "details": details_dict,
        }
