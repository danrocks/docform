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
    get_workgroup_repository,
    get_workgroup_user_repository,
    get_workitem_repository,
)
from tenant_context import verify_tenant_match

router = APIRouter()

VALID_STATUSES = {"draft", "active", "completed", "cancelled"}


class WorkitemCreate(BaseModel):
    name: str
    description: Optional[str] = ""


class WorkitemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


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


def _require_workgroup_member(workgroup_id: str, current_user: dict) -> None:
    if current_user["role"] == "admin":
        return
    wu_repo = get_workgroup_user_repository()
    members = wu_repo.get_workgroup_users(workgroup_id)
    member_ids = [m["user_id"] for m in members]
    if current_user["id"] not in member_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workgroup")


def _require_workitem_access(workitem: dict, current_user: dict) -> None:
    if current_user["role"] == "admin":
        return
    if workitem.get("created_by") != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")


@router.post("/{workgroup_id}/workitems", status_code=status.HTTP_201_CREATED)
def create_workitem(
    workgroup_id: str,
    body: WorkitemCreate,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    tid = _tenant_id(current_user)
    wg = _get_workgroup_or_404(workgroup_id, tid)
    _require_workgroup_member(workgroup_id, current_user)

    repo = get_workitem_repository()
    if repo.name_exists_in_workgroup(workgroup_id, body.name):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A workitem with this name already exists in the workgroup")

    workitem = {
        "id": str(uuid.uuid4()),
        "workgroup_id": workgroup_id,
        "name": body.name,
        "description": body.description or "",
        "status": "draft",
        "tenant_id": wg.get("tenant_id", tid),
        "created_at": utcnow_iso(),
        "created_by": current_user["id"],
    }
    return repo.create(workitem)


@router.get("/{workgroup_id}/workitems")
def list_workitems(
    workgroup_id: str,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    tid = _tenant_id(current_user)
    _get_workgroup_or_404(workgroup_id, tid)
    _require_workgroup_member(workgroup_id, current_user)
    return get_workitem_repository().get_by_workgroup(workgroup_id)


@router.get("/{workgroup_id}/workitems/{workitem_id}")
def get_workitem(
    workgroup_id: str,
    workitem_id: str,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    tid = _tenant_id(current_user)
    _get_workgroup_or_404(workgroup_id, tid)
    _require_workgroup_member(workgroup_id, current_user)

    repo = get_workitem_repository()
    wi = repo.get_by_id(workitem_id)
    if not wi or wi.get("workgroup_id") != workgroup_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workitem not found")
    return wi


@router.put("/{workgroup_id}/workitems/{workitem_id}")
def update_workitem(
    workgroup_id: str,
    workitem_id: str,
    body: WorkitemUpdate,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    tid = _tenant_id(current_user)
    _get_workgroup_or_404(workgroup_id, tid)
    _require_workgroup_member(workgroup_id, current_user)

    repo = get_workitem_repository()
    wi = repo.get_by_id(workitem_id)
    if not wi or wi.get("workgroup_id") != workgroup_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workitem not found")

    _require_workitem_access(wi, current_user)

    data = body.model_dump(exclude_none=True)
    if not data:
        return wi

    if "status" in data and data["status"] not in VALID_STATUSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}")

    if "name" in data and data["name"] != wi.get("name"):
        if repo.name_exists_in_workgroup(workgroup_id, data["name"], exclude_id=workitem_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A workitem with this name already exists in the workgroup")

    return repo.update(workitem_id, data)


@router.delete("/{workgroup_id}/workitems/{workitem_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workitem(
    workgroup_id: str,
    workitem_id: str,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    tid = _tenant_id(current_user)
    _get_workgroup_or_404(workgroup_id, tid)
    _require_workgroup_member(workgroup_id, current_user)

    repo = get_workitem_repository()
    wi = repo.get_by_id(workitem_id)
    if not wi or wi.get("workgroup_id") != workgroup_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workitem not found")

    _require_workitem_access(wi, current_user)
    repo.delete(workitem_id)
    return None
