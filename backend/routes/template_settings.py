import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from file_utils import utcnow_iso
from repositories.factory import get_template_settings_repository
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


class TemplateSettingsCreate(BaseModel):
    template_id: str
    restricted_to_workgroups: Optional[bool] = False


class TemplateSettingsUpdate(BaseModel):
    restricted_to_workgroups: Optional[bool] = None


@router.get("/{template_id}")
def get_template_settings(
    template_id: str,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    tid = _tenant_id(current_user)
    entry = get_template_settings_repository().get_by_template_id(template_id)
    if not entry or entry.get("tenant_id") != tid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template settings not found")
    return entry


@router.post("", status_code=status.HTTP_201_CREATED)
def create_template_settings(
    body: TemplateSettingsCreate,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    _require_admin(current_user)
    tid = _tenant_id(current_user)
    repo = get_template_settings_repository()
    if repo.get_by_template_id(body.template_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Template settings already exist",
        )
    entry = {
        "template_id": body.template_id,
        "tenant_id": tid,
        "restricted_to_workgroups": bool(body.restricted_to_workgroups),
        "created_at": utcnow_iso(),
        "created_by": current_user["id"],
    }
    return repo.create(entry)


@router.put("/{template_id}")
def update_template_settings(
    template_id: str,
    body: TemplateSettingsUpdate,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    _require_admin(current_user)
    tid = _tenant_id(current_user)
    repo = get_template_settings_repository()
    existing = repo.get_by_template_id(template_id)
    if not existing or existing.get("tenant_id") != tid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template settings not found")
    data = body.model_dump(exclude_none=True)
    if not data:
        return existing
    return repo.update(template_id, data)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template_settings(
    template_id: str,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    _require_admin(current_user)
    tid = _tenant_id(current_user)
    repo = get_template_settings_repository()
    existing = repo.get_by_template_id(template_id)
    if not existing or existing.get("tenant_id") != tid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template settings not found")
    repo.delete(template_id)
    return None
