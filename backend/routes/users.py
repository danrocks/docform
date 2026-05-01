import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
from fastapi import APIRouter, HTTPException, status, Depends, Query, Request
from pydantic import BaseModel, field_validator
from typing import Optional
from auth_utils import require_role, hash_password, get_current_user
from repositories.factory import get_role_repository, get_user_repository
from validators import validate_password, validate_username
from tenant_context import verify_tenant_match


def validate_role(role: str) -> None:
    role_repo = get_role_repository()
    if not role_repo.get_by_name(role):
        valid = [r["name"] for r in role_repo.get_all()]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role '{role}'. Valid roles: {valid}",
        )


def strip_password(u: dict) -> dict:
    return {k: v for k, v in u.items() if k != "password"}


def _effective_tenant_id(current_user: dict) -> str:
    """Return the tenant_id to scope queries to. Superadmin has None."""
    return current_user.get("tenant_id")


router = APIRouter()


class UserCreate(BaseModel):
    username: str
    password: str
    role: str
    name: str
    tenant_id: Optional[str] = None

    @field_validator("username")
    @classmethod
    def check_username(cls, v: str) -> str:
        return validate_username(v)

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password(v)


class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    name: Optional[str] = None

    @field_validator("username")
    @classmethod
    def check_username(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_username(v)
        return v

    @field_validator("password")
    @classmethod
    def check_password(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_password(v)
        return v


@router.get("")
def list_users(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(verify_tenant_match),
):
    if current_user["role"] not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Not permitted")
    repo = get_user_repository()
    tid = _effective_tenant_id(current_user)
    return {
        "users": [strip_password(u) for u in repo.get_paginated(skip, limit, tenant_id=tid)],
        "total": repo.count(tenant_id=tid),
        "skip": skip,
        "limit": limit,
    }


@router.get("/{user_id}/public")
def get_user_public(user_id: str, current_user: dict = Depends(verify_tenant_match)):
    repo = get_user_repository()
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    tid = _effective_tenant_id(current_user)
    if tid is not None and user.get("tenant_id") != tid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"id": user["id"], "name": user["name"], "role": user["role"]}


@router.get("/{user_id}")
def get_user(user_id: str, current_user: dict = Depends(verify_tenant_match)):
    if current_user["role"] not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Not permitted")
    repo = get_user_repository()
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    tid = _effective_tenant_id(current_user)
    if tid is not None and user.get("tenant_id") != tid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return strip_password(user)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, request: Request, current_user: dict = Depends(verify_tenant_match)):
    if current_user["role"] not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Not permitted")
    validate_role(body.role)
    repo = get_user_repository()

    if current_user["role"] == "superadmin" and body.tenant_id is not None:
        assign_tenant_id = body.tenant_id
    else:
        assign_tenant_id = current_user.get("tenant_id")

    if repo.get_by_username(body.username, tenant_id=assign_tenant_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{body.username}' already exists",
        )
    user = {
        "id": str(uuid.uuid4()),
        "username": body.username,
        "password": hash_password(body.password),
        "role": body.role,
        "name": body.name,
        "tenant_id": assign_tenant_id,
    }
    created = repo.create(user)
    return strip_password(created)


@router.put("/{user_id}")
def update_user(user_id: str, body: UserUpdate, current_user: dict = Depends(verify_tenant_match)):
    if current_user["role"] not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Not permitted")
    repo = get_user_repository()
    existing = repo.get_by_id(user_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    tid = _effective_tenant_id(current_user)
    if tid is not None and existing.get("tenant_id") != tid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    data = body.model_dump(exclude_none=True)
    if user_id == current_user["id"] and "role" in data and data["role"] != current_user["role"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot change your own role",
        )
    if "username" in data:
        conflict = repo.get_by_username(data["username"], tenant_id=existing.get("tenant_id"))
        if conflict and conflict["id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Username '{data['username']}' already exists",
            )
    if "role" in data:
        validate_role(data["role"])
    if "password" in data:
        data["password"] = hash_password(data["password"])

    updated = repo.update(user_id, data)
    return strip_password(updated)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, current_user: dict = Depends(verify_tenant_match)):
    if current_user["role"] not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Not permitted")
    if user_id == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete your own account",
        )
    repo = get_user_repository()
    existing = repo.get_by_id(user_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    tid = _effective_tenant_id(current_user)
    if tid is not None and existing.get("tenant_id") != tid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not repo.delete(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
