import sys
import os
import re
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator

from auth_utils import require_role
from tenant_context import RESERVED_SLUGS, is_admin_subdomain, verify_tenant_match

router = APIRouter()

BACKEND_ROOT = Path(__file__).resolve().parent.parent
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _require_admin_subdomain(request: Request):
    if not is_admin_subdomain(request):
        raise HTTPException(status_code=404, detail="Not found")


class TenantCreate(BaseModel):
    name: str
    slug: str

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        v = v.lower().strip()
        if not SLUG_PATTERN.match(v):
            raise ValueError("Slug must be lowercase alphanumeric with hyphens only")
        if v in RESERVED_SLUGS:
            raise ValueError(f"Slug '{v}' is reserved")
        return v


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    active: Optional[str] = None


@router.get("")
def list_tenants(
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    _require_admin_subdomain(request)
    if current_user["role"] != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin required")
    from repositories.factory import get_tenant_repository
    return get_tenant_repository().get_all()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_tenant(
    body: TenantCreate,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    _require_admin_subdomain(request)
    if current_user["role"] != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin required")

    from repositories.factory import get_tenant_repository
    repo = get_tenant_repository()

    if repo.get_by_slug(body.slug):
        raise HTTPException(status_code=409, detail=f"Slug '{body.slug}' already exists")

    tenant_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    tenant = {
        "id": tenant_id,
        "name": body.name,
        "slug": body.slug,
        "active": "true",
        "created_at": now,
    }
    created = repo.create(tenant)

    for subdir in [
        BACKEND_ROOT / "data" / "templates" / tenant_id,
        BACKEND_ROOT / "data" / "submissions" / tenant_id,
        BACKEND_ROOT / "uploads" / "generated" / tenant_id,
    ]:
        subdir.mkdir(parents=True, exist_ok=True)

    return created


@router.get("/{tenant_id}")
def get_tenant(
    tenant_id: str,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    _require_admin_subdomain(request)
    if current_user["role"] != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin required")
    from repositories.factory import get_tenant_repository
    tenant = get_tenant_repository().get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.put("/{tenant_id}")
def update_tenant(
    tenant_id: str,
    body: TenantUpdate,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    _require_admin_subdomain(request)
    if current_user["role"] != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin required")
    from repositories.factory import get_tenant_repository
    data = body.model_dump(exclude_none=True)
    if not data:
        tenant = get_tenant_repository().get_by_id(tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        return tenant
    updated = get_tenant_repository().update(tenant_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return updated


@router.delete("/{tenant_id}")
def delete_tenant(
    tenant_id: str,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    _require_admin_subdomain(request)
    if current_user["role"] != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin required")
    from repositories.factory import get_tenant_repository
    repo = get_tenant_repository()
    tenant = repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    repo.update(tenant_id, {"active": "false"})
    return {"detail": "Tenant deactivated"}
