from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os, json
from pathlib import Path

# Read optional AI configuration from environment
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

from routes import auth, templates, submissions

DATA_DIRS = [
    "data/templates",
    "data/submissions",
    "uploads/templates",
    "uploads/generated",
]

# Create directories eagerly at import time so StaticFiles mount doesn't crash
for _d in DATA_DIRS:
    Path(_d).mkdir(parents=True, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    users_file = Path("data/users.json")
    if not users_file.exists():
        from auth_utils import hash_password
        default_users = [
            {"id": "1", "username": "admin",    "password": hash_password("admin123"),    "role": "admin",    "name": "Admin User"},
            {"id": "2", "username": "staff",    "password": hash_password("staff123"),    "role": "staff",    "name": "Staff User"},
            {"id": "3", "username": "approver", "password": hash_password("approver123"), "role": "approver", "name": "Approver User"},
        ]
        users_file.write_text(json.dumps(default_users, indent=2))
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

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/api/health")
def health():
    return {"status": "ok"}
