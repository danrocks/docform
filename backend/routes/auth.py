import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from jose import jwt
from auth_utils import (
    verify_password, create_access_token, get_current_user, hash_password,
    oauth2_scheme, revoke_token, SECRET_KEY, ALGORITHM,
)
from repositories.factory import get_user_repository
from rate_limit import check_rate_limit, record_failure, reset
from validators import validate_password
from tenant_context import get_current_tenant, is_admin_subdomain, verify_tenant_match
from config import settings

router = APIRouter()


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


@router.post("/login", response_model=LoginResponse)
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    ip = request.client.host
    check_rate_limit(ip)

    tenant = get_current_tenant(request)

    if is_admin_subdomain(request):
        print(  "Admin subdomain access - skipping tenant check")
        tenant_id = None
    elif tenant:
        tenant_id = tenant["id"]
    else:
        raise HTTPException(status_code=404, detail="Not found")

    repo = get_user_repository()
    user = repo.get_by_username(form_data.username, tenant_id=tenant_id)
    if not user or not verify_password(form_data.password, user["password"]):
        record_failure(ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    reset(ip)
    token = create_access_token({"sub": user["id"], "role": user["role"], "tenant_id": user.get("tenant_id")})
    safe_user = {k: v for k, v in user.items() if k != "password"}
    return {"access_token": token, "token_type": "bearer", "user": safe_user}


@router.get("/me")
def me(current_user: dict = Depends(verify_tenant_match)):
    return {k: v for k, v in current_user.items() if k != "password"}


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(json_schema_extra={"minLength": settings.MIN_PASSWORD_LENGTH})


@router.put("/me/password")
def change_password(body: PasswordChange, current_user: dict = Depends(verify_tenant_match)):
    if not verify_password(body.current_password, current_user["password"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    try:
        validate_password(body.new_password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    repo = get_user_repository()
    repo.update(current_user["id"], {"password": hash_password(body.new_password)})
    return {"detail": "Password updated successfully"}


@router.post("/logout")
def logout(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        if jti:
            revoke_token(jti)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    return {"detail": "Logged out successfully"}
