import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
from typing import Optional
from auth_utils import require_role, hash_password
from repositories.factory import get_role_repository, get_user_repository


def validate_role(role: str) -> None:
    role_repo = get_role_repository()
    if not role_repo.get_by_name(role):
        valid = [r["name"] for r in role_repo.get_all()]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role '{role}'. Valid roles: {valid}",
        )

router = APIRouter()


class UserCreate(BaseModel):
    username: str
    password: str
    role: str
    name: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    name: Optional[str] = None


@router.get("")
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(require_role("admin")),
):
    repo = get_user_repository()
    users = repo.get_all()
    paginated = users[skip : skip + limit]
    return {
        "users": [{k: v for k, v in u.items() if k != "password"} for u in paginated],
        "total": len(users),
        "skip": skip,
        "limit": limit,
    }


@router.get("/{user_id}")
def get_user(user_id: str, current_user: dict = Depends(require_role("admin"))):
    repo = get_user_repository()
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {k: v for k, v in user.items() if k != "password"}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, current_user: dict = Depends(require_role("admin"))):
    validate_role(body.role)
    repo = get_user_repository()
    if repo.get_by_username(body.username):
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
    }
    created = repo.create(user)
    return {k: v for k, v in created.items() if k != "password"}


@router.put("/{user_id}")
def update_user(user_id: str, body: UserUpdate, current_user: dict = Depends(require_role("admin"))):
    repo = get_user_repository()
    existing = repo.get_by_id(user_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    data = body.model_dump(exclude_none=True)
    if user_id == current_user["id"] and "role" in data and data["role"] != current_user["role"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot change your own role",
        )
    if "username" in data:
        conflict = repo.get_by_username(data["username"])
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
    return {k: v for k, v in updated.items() if k != "password"}


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, current_user: dict = Depends(require_role("admin"))):
    if user_id == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete your own account",
        )
    repo = get_user_repository()
    if not repo.delete(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
