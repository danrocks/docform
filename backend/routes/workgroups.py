import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from auth_utils import get_current_user
from file_utils import utcnow_iso
from repositories.factory import (
    get_template_settings_repository,
    get_user_repository,
    get_workgroup_repository,
    get_workgroup_template_repository,
    get_workgroup_user_repository,
)
from tenant_context import verify_tenant_match

router = APIRouter()


def _require_admin(current_user: dict) -> None:
    if current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")


def _tenant_id(current_user: dict) -> str:
    tid = current_user.get("tenant_id")
    if not tid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context required")
    return tid


def _get_workgroup_or_404(workgroup_id: str, tenant_id: str) -> dict:
    repo = get_workgroup_repository()
    wg = repo.get_by_id(workgroup_id)
    if not wg or wg.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workgroup not found")
    return wg


class WorkgroupCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    requires_approval: Optional[bool] = False


class WorkgroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    requires_approval: Optional[bool] = None


class WorkgroupUserBody(BaseModel):
    user_id: str


class WorkgroupTemplateBody(BaseModel):
    template_id: str


@router.get("")
def list_workgroups(
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    _require_admin(current_user)
    tid = _tenant_id(current_user)
    return get_workgroup_repository().get_all(tenant_id=tid)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_workgroup(
    body: WorkgroupCreate,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    _require_admin(current_user)
    tid = _tenant_id(current_user)
    repo = get_workgroup_repository()
    workgroup = {
        "id": str(uuid.uuid4()),
        "name": body.name,
        "description": body.description or "",
        "tenant_id": tid,
        "requires_approval": bool(body.requires_approval),
        "created_at": utcnow_iso(),
        "created_by": current_user["id"],
    }
    return repo.create(workgroup)


@router.get("/{workgroup_id}")
def get_workgroup(
    workgroup_id: str,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    _require_admin(current_user)
    tid = _tenant_id(current_user)
    return _get_workgroup_or_404(workgroup_id, tid)


@router.put("/{workgroup_id}")
def update_workgroup(
    workgroup_id: str,
    body: WorkgroupUpdate,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    _require_admin(current_user)
    tid = _tenant_id(current_user)
    _get_workgroup_or_404(workgroup_id, tid)
    data = body.model_dump(exclude_none=True)
    if not data:
        return get_workgroup_repository().get_by_id(workgroup_id)
    return get_workgroup_repository().update(workgroup_id, data)


@router.delete("/{workgroup_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workgroup(
    workgroup_id: str,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    _require_admin(current_user)
    tid = _tenant_id(current_user)
    _get_workgroup_or_404(workgroup_id, tid)
    get_workgroup_repository().delete(workgroup_id)
    return None


@router.get("/{workgroup_id}/users")
def list_workgroup_users(
    workgroup_id: str,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    _require_admin(current_user)
    tid = _tenant_id(current_user)
    _get_workgroup_or_404(workgroup_id, tid)
    return get_workgroup_user_repository().get_workgroup_users(workgroup_id)


@router.post("/{workgroup_id}/users", status_code=status.HTTP_201_CREATED)
def add_workgroup_user(
    workgroup_id: str,
    body: WorkgroupUserBody,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    _require_admin(current_user)
    tid = _tenant_id(current_user)
    _get_workgroup_or_404(workgroup_id, tid)

    user = get_user_repository().get_by_id(body.user_id)
    if not user or user.get("tenant_id") != tid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return get_workgroup_user_repository().add_user(workgroup_id, body.user_id)


@router.delete(
    "/{workgroup_id}/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_workgroup_user(
    workgroup_id: str,
    user_id: str,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    _require_admin(current_user)
    tid = _tenant_id(current_user)
    _get_workgroup_or_404(workgroup_id, tid)
    removed = get_workgroup_user_repository().remove_user(workgroup_id, user_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")
    return None


@router.get("/{workgroup_id}/templates")
def list_workgroup_templates(
    workgroup_id: str,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    _require_admin(current_user)
    tid = _tenant_id(current_user)
    _get_workgroup_or_404(workgroup_id, tid)
    return get_workgroup_template_repository().get_workgroup_templates(workgroup_id)


@router.post("/{workgroup_id}/templates", status_code=status.HTTP_201_CREATED)
def add_workgroup_template(
    workgroup_id: str,
    body: WorkgroupTemplateBody,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    _require_admin(current_user)
    tid = _tenant_id(current_user)
    _get_workgroup_or_404(workgroup_id, tid)

    ts_repo = get_template_settings_repository()
    settings_entry = ts_repo.get_by_template_id(body.template_id)
    if not settings_entry:
        settings_entry = ts_repo.create({
            "template_id": body.template_id,
            "tenant_id": tid,
            "restricted_to_workgroups": False,
            "created_at": utcnow_iso(),
            "created_by": current_user["id"],
        })
    elif settings_entry.get("tenant_id") != tid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    return get_workgroup_template_repository().add_template(workgroup_id, body.template_id)


@router.delete(
    "/{workgroup_id}/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_workgroup_template(
    workgroup_id: str,
    template_id: str,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    _require_admin(current_user)
    tid = _tenant_id(current_user)
    _get_workgroup_or_404(workgroup_id, tid)
    removed = get_workgroup_template_repository().remove_template(workgroup_id, template_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")
    return None
