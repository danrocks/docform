"""
Shared file-system helpers for tenant-scoped data directories and atomic writes.
"""

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, Request

from tenant_context import get_current_tenant, is_tenant_subdomain

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parent

# Fixed filenames inside each per-template subdirectory
TEMPLATE_META_FILENAME = "meta.json"
TEMPLATE_INTERVIEW_FILENAME = "interview.json"
TEMPLATE_DOCX_FILENAME = "template.docx"


# ---------------------------------------------------------------------------
# Tenant-scoped directory helpers (#11)
# ---------------------------------------------------------------------------

def get_tenant_data_dir(request: Request, *sub_path: str) -> Path:
    """Return a tenant-scoped data directory, creating it if needed.

    Usage:
        get_tenant_data_dir(request, "data", "templates")
        get_tenant_data_dir(request, "uploads", "generated")
    """
    if not is_tenant_subdomain(request):
        raise HTTPException(status_code=403, detail="Tenant-scoped only")
    tenant = get_current_tenant(request)
    if not tenant:
        raise HTTPException(status_code=403, detail="Tenant-scoped only")
    path = BACKEND_ROOT / Path(*sub_path) / tenant["id"]
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_template_subdir(templates_dir: Path, template_id: str) -> Path:
    """Return the per-template subdirectory, creating it if needed."""
    path = templates_dir / template_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_workgroup_subdir(base_dir: Path, workgroup_id: str) -> Path:
    """Return the per-workgroup subdirectory under *base_dir*, creating it if needed.

    Used to namespace submissions and generated artefacts by workgroup so that
    files for different workgroups don't collide and can be enumerated cheaply.
    """
    path = base_dir / "workgroups" / workgroup_id
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# Atomic write helpers (#2)
# ---------------------------------------------------------------------------

def atomic_write_text(path: Path, content: str) -> None:
    """Write *content* to *path* atomically via write-to-temp-then-rename."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        os.replace(tmp, str(path))
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write *data* to *path* atomically via write-to-temp-then-rename."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        os.write(fd, data)
        os.close(fd)
        os.replace(tmp, str(path))
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def atomic_write_json(path: Path, obj: object) -> None:
    """Serialize *obj* as pretty-printed JSON and write atomically."""
    atomic_write_text(path, json.dumps(obj, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Timestamp helper (#10)
# ---------------------------------------------------------------------------

def utcnow_iso() -> str:
    """Return the current UTC time as an ISO-8601 string with timezone."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Submission counting (#1)
# ---------------------------------------------------------------------------

def count_submissions(submissions_dir: Path, template_id: str) -> int:
    """Count submission files for *template_id* in *submissions_dir*."""
    if not submissions_dir.exists():
        return 0
    count = 0
    for f in submissions_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            if data.get("template_id") == template_id:
                count += 1
        except Exception:
            continue
    return count
