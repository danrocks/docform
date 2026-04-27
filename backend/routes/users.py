import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional
from auth_utils import require_role, hash_password
from repositories.factory import get_user_repository

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
def list_users(current_user: dict = Depends(require_role("admin"))):
    repo = get_user_repository()
    users = repo.get_all()
    return [{k: v for k, v in u.items() if k != "password"} for u in users]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, current_user: dict = Depends(require_role("admin"))):
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
    if "password" in data:
        data["password"] = hash_password(data["password"])

    updated = repo.update(user_id, data)
    return {k: v for k, v in updated.items() if k != "password"}


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, current_user: dict = Depends(require_role("admin"))):
    repo = get_user_repository()
    if not repo.delete(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
