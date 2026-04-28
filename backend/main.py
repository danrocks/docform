from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os, json
from pathlib import Path
from config import settings
# Read optional AI configuration from environment
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", settings.OPENAI_API_KEY)
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

from routes import auth, templates, submissions, users, roles
from repositories.factory import get_role_repository, get_user_repository

BACKEND_ROOT = Path(__file__).resolve().parent

# DATA_DIRS = [
#     "data/templates",
#     "data/submissions",
#     "uploads/templates",
#     "uploads/generated",
# ]
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

    repo = get_user_repository()
    if repo.count() == 0:
        from auth_utils import hash_password
        repo.create({"id": "1", "username": "admin", "password": hash_password("admin123"), "role": "admin", "name": "Admin User"})
        repo.create({"id": "2", "username": "staff", "password": hash_password("staff123"), "role": "staff", "name": "Staff User"})
        repo.create({"id": "3", "username": "approver", "password": hash_password("approver123"), "role": "approver", "name": "Approver User"})
    yield

app = FastAPI(title="DocForm API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,        prefix="/api/auth",        tags=["auth"])
app.include_router(templates.router,   prefix="/api/templates",   tags=["templates"])
app.include_router(submissions.router, prefix="/api/submissions",  tags=["submissions"])
app.include_router(users.router,       prefix="/api/users",       tags=["users"])
app.include_router(roles.router,       prefix="/api/roles",       tags=["roles"])

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/api/health")
def health():
    return {"status": "ok"}
