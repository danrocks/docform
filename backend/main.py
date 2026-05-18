from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os, json
from pathlib import Path
from datetime import datetime
from config import settings
# Read optional AI configuration from environment
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", settings.OPENAI_API_KEY)
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

from routes import auth, templates, submissions, users, roles, tenants, workgroups, template_settings
from repositories.factory import get_role_repository, get_user_repository, get_tenant_repository

BACKEND_ROOT = Path(__file__).resolve().parent

DATA_DIRS = [  
    BACKEND_ROOT / "data" / "templates",  
    BACKEND_ROOT / "data" / "submissions",  
    BACKEND_ROOT / "uploads" / "templates",  
    BACKEND_ROOT / "uploads" / "generated",  
]
# Create directories eagerly at import time so StaticFiles mount doesn't crash
for _d in DATA_DIRS:
    Path(_d).mkdir(parents=True, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.STORAGE_BACKEND != "json":
        from repositories.db_repo import create_tables
        create_tables()

    role_repo = get_role_repository()
    if role_repo.count() == 0:
        role_repo.create({"name": "admin", "description": "Administrator"})
        role_repo.create({"name": "staff", "description": "Staff member"})
        role_repo.create({"name": "approver", "description": "Approver"})
        role_repo.create({"name": "superadmin", "description": "Super administrator - manages tenants"})

    tenant_repo = get_tenant_repository()
    if tenant_repo.count() == 0:
        now = datetime.utcnow().isoformat()
        tenant_repo.create({"id": "tenant-1", "name": "Demo Business", "slug": "demo", "active": "true", "created_at": now})
        tenant_repo.create({"id": "tenant-2", "name": "Girl Guides Troop 7", "slug": "girlguides", "active": "true", "created_at": now})

        for tid in ("tenant-1", "tenant-2"):
            for subdir in (
                BACKEND_ROOT / "data" / "templates" / tid,
                BACKEND_ROOT / "data" / "submissions" / tid,
                BACKEND_ROOT / "uploads" / "generated" / tid,
            ):
                subdir.mkdir(parents=True, exist_ok=True)

    repo = get_user_repository()
    if repo.count() == 0:
        from auth_utils import hash_password
        repo.create({"id": "0", "username": "superadmin", "password": hash_password("super123"), "role": "superadmin", "name": "Super Admin", "tenant_id": None})
        repo.create({"id": "1", "username": "admin", "password": hash_password("admin123"), "role": "admin", "name": "Admin T1", "tenant_id": "tenant-1"})
        repo.create({"id": "2", "username": "staff", "password": hash_password("staff123"), "role": "staff", "name": "Staff T1", "tenant_id": "tenant-1"})
        repo.create({"id": "3", "username": "admin", "password": hash_password("admin123"), "role": "admin", "name": "Admin T2", "tenant_id": "tenant-2"})
        repo.create({"id": "4", "username": "staff", "password": hash_password("staff123"), "role": "staff", "name": "Staff T2", "tenant_id": "tenant-2"})
    yield

app = FastAPI(title="DocForm API", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    error_msg = exc.errors()[0]["msg"] if exc.errors() else "Validation error"
    return JSONResponse(
        status_code=422,
        content={"detail": error_msg},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(\w[\w-]*\.)?localhost(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,        prefix="/api/auth",        tags=["auth"])
app.include_router(templates.router,   prefix="/api/templates",   tags=["templates"])
app.include_router(submissions.router, prefix="/api/submissions",  tags=["submissions"])
app.include_router(users.router,       prefix="/api/users",       tags=["users"])
app.include_router(roles.router,       prefix="/api/roles",       tags=["roles"])
app.include_router(tenants.router,     prefix="/api/tenants",     tags=["tenants"])
app.include_router(workgroups.router,  prefix="/api/workgroups",  tags=["workgroups"])
app.include_router(template_settings.router, prefix="/api/template-settings", tags=["template-settings"])

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/api/health")
def health():
    return {"status": "ok"}
