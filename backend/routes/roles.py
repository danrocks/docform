import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from auth_utils import require_role, get_current_user
from repositories.factory import get_role_repository, get_user_repository

router = APIRouter()


class RoleCreate(BaseModel):
    name: str
    description: str = ""


@router.get("")
def list_roles(current_user: dict = Depends(get_current_user)):
    repo = get_role_repository()
    return repo.get_all()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_role(body: RoleCreate, current_user: dict = Depends(require_role("admin"))):
    repo = get_role_repository()
    if repo.get_by_name(body.name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Role '{body.name}' already exists",
        )
    return repo.create({"name": body.name, "description": body.description})


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(name: str, current_user: dict = Depends(require_role("admin"))):
    repo = get_role_repository()
    user_repo = get_user_repository()
    users_with_role = [u for u in user_repo.get_all() if u["role"] == name]
    if users_with_role:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete role '{name}': {len(users_with_role)} user(s) still assigned to it",
        )
    if not repo.delete(name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
