import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import List, Optional

from docxtpl import DocxTemplate
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from auth_utils import get_current_user
from file_utils import (
    BACKEND_ROOT,
    TEMPLATE_DOCX_FILENAME,
    TEMPLATE_INTERVIEW_FILENAME,
    TEMPLATE_META_FILENAME,
    atomic_write_json,
    get_tenant_data_dir,
    get_workgroup_subdir,
    utcnow_iso,
)
from question_schema import validate_submission_data
from repositories.factory import (
    get_answerset_metadata_repository,
    get_audit_log_repository,
    get_template_settings_repository,
    get_workgroup_repository,
    get_workgroup_template_repository,
    get_workgroup_user_repository,
)
from tenant_context import verify_tenant_match

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class AnswersetCreate(BaseModel):
    template_id: str
    data: dict
    context: Optional[str] = ""
    workgroup_id: Optional[str] = None


class AnswersetUpdate(BaseModel):
    data: dict
    context: Optional[str] = None
    version: int


class AnswersetShare(BaseModel):
    shared_with: List[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_submissions_dir(request: Request, workgroup_id: Optional[str] = None) -> Path:
    base = get_tenant_data_dir(request, "data", "submissions")
    if workgroup_id:
        return get_workgroup_subdir(base, workgroup_id)
    return base


def _get_templates_dir(request: Request) -> Path:
    return get_tenant_data_dir(request, "data", "templates")


def _get_generated_dir(request: Request, workgroup_id: Optional[str] = None) -> Path:
    base = get_tenant_data_dir(request, "uploads", "generated")
    if workgroup_id:
        return get_workgroup_subdir(base, workgroup_id)
    return base


def _user_workgroup_ids(user_id: str) -> list[str]:
    links = get_workgroup_user_repository().get_user_workgroups(user_id)
    return [r["workgroup_id"] for r in links]


def _user_has_template_access(
    template_id: str, current_user: dict, tenant_id: Optional[str]
) -> bool:
    if current_user.get("role") == "admin":
        return True
    settings_entry = get_template_settings_repository().get_by_template_id(template_id)
    if not settings_entry or not settings_entry.get("restricted_to_workgroups"):
        return True
    if tenant_id is not None and settings_entry.get("tenant_id") != tenant_id:
        return False
    user_links = get_workgroup_user_repository().get_user_workgroups(current_user["id"])
    user_workgroup_ids = {r["workgroup_id"] for r in user_links}
    if not user_workgroup_ids:
        return False
    template_links = get_workgroup_template_repository().get_template_workgroups(template_id)
    template_workgroup_ids = {r["workgroup_id"] for r in template_links}
    return bool(user_workgroup_ids & template_workgroup_ids)


def _check_answerset_access(meta: dict, current_user: dict) -> None:
    """Verify user can access this answerset based on permissions."""
    if current_user["role"] in ("admin", "approver"):
        return
    user_id = current_user["id"]
    if meta.get("submitted_by") == user_id:
        return
    if user_id in (meta.get("shared_with") or []):
        return
    wg_id = meta.get("workgroup_id")
    if wg_id:
        user_wgs = _user_workgroup_ids(user_id)
        if wg_id in user_wgs:
            return
    raise HTTPException(status_code=403, detail="Access denied")


def _audit_log(
    request: Request,
    answerset_id: str,
    operation: str,
    user: dict,
    details: Optional[dict] = None,
) -> None:
    repo = get_audit_log_repository()
    ip = request.client.host if request.client else "unknown"
    entry = {
        "id": str(uuid.uuid4()),
        "answerset_id": answerset_id,
        "operation": operation,
        "user_id": user["id"],
        "user_name": user.get("name", user.get("username", "")),
        "tenant_id": user.get("tenant_id"),
        "ip_address": ip,
        "timestamp": utcnow_iso(),
        "details": details or {},
    }
    repo.create(entry)


def _generate_documents(template: dict, submission: dict, template_dir: Path, generated_dir: Path):
    """Fill the docx template and convert to PDF."""
    generated_dir.mkdir(parents=True, exist_ok=True)
    src = template_dir / TEMPLATE_DOCX_FILENAME
    if not src.exists():
        raise FileNotFoundError(f"Template file not found: {src}")

    sid = submission["id"]
    docx_out = generated_dir / f"{sid}.docx"
    pdf_out = generated_dir / f"{sid}.pdf"

    tpl = DocxTemplate(src)
    tpl.render(submission["data"])
    tpl.save(docx_out)

    lo_path = shutil.which("libreoffice") or shutil.which("soffice")
    if lo_path:
        result = subprocess.run(
            [lo_path, "--headless", "--convert-to", "pdf", "--outdir", str(generated_dir), str(docx_out)],
            capture_output=True, timeout=30,
        )
        if result.returncode != 0:
            pdf_out = None
    else:
        pdf_out = None

    return docx_out, pdf_out


def _find_answerset_file(request: Request, answerset_id: str, workgroup_id: Optional[str] = None) -> Path:
    """Locate the answerset JSON file on disk."""
    base = _get_submissions_dir(request, workgroup_id=workgroup_id)
    path = base / f"{answerset_id}.json"
    if path.exists():
        return path
    if not workgroup_id:
        wg_root = _get_submissions_dir(request) / "workgroups"
        if wg_root.exists():
            for wg_dir in wg_root.iterdir():
                if not wg_dir.is_dir():
                    continue
                candidate = wg_dir / f"{answerset_id}.json"
                if candidate.exists():
                    return candidate
    raise HTTPException(status_code=404, detail="Answerset file not found")


def _calculate_completion(data: dict, fields: list) -> float:
    """Calculate completion percentage based on filled fields."""
    if not fields:
        return 100.0
    total = 0
    filled = 0

    def walk(components):
        nonlocal total, filled
        for c in components:
            if not c:
                continue
            if c.get("type") == "dialog":
                walk(c.get("components") or [])
            elif c.get("type") == "repeat":
                pass
            else:
                total += 1
                cid = c.get("id")
                if cid and cid in data:
                    val = data[cid]
                    if val is not None and val != "" and val != []:
                        filled += 1

    walk(fields)
    if total == 0:
        return 100.0
    return round((filled / total) * 100, 1)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/")
def list_answersets(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    template_id: Optional[str] = None,
    workgroup_id: Optional[str] = None,
    current_user: dict = Depends(verify_tenant_match),
):
    meta_repo = get_answerset_metadata_repository()
    tenant_id = current_user.get("tenant_id")

    if current_user["role"] in ("admin", "approver"):
        user_id = None
        workgroup_ids = None
    else:
        user_id = current_user["id"]
        workgroup_ids = _user_workgroup_ids(user_id)

    if workgroup_id:
        if user_id and workgroup_id not in (workgroup_ids or []):
            raise HTTPException(status_code=403, detail="Not a member of this workgroup")
        items = meta_repo.get_by_workgroup(workgroup_id)
        total = len(items)
        items = sorted(items, key=lambda x: x.get("submitted_at", ""), reverse=True)
        items = items[skip:skip + limit]
    else:
        items = meta_repo.get_paginated(
            skip=skip, limit=limit, tenant_id=tenant_id,
            user_id=user_id, workgroup_ids=workgroup_ids,
            template_id=template_id,
        )
        total = meta_repo.count(tenant_id=tenant_id, user_id=user_id, workgroup_ids=workgroup_ids)

    return {"answersets": items, "total": total, "skip": skip, "limit": limit}


@router.get("/{answerset_id}")
def get_answerset(
    answerset_id: str,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    meta_repo = get_answerset_metadata_repository()
    meta = meta_repo.get_by_id(answerset_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Answerset not found")

    _check_answerset_access(meta, current_user)
    _audit_log(request, answerset_id, "access", current_user)

    path = _find_answerset_file(request, answerset_id, workgroup_id=meta.get("workgroup_id"))
    answerset = json.loads(path.read_text())

    templates_dir = _get_templates_dir(request)
    template_dir = templates_dir / meta["template_id"]
    interview_path = template_dir / TEMPLATE_INTERVIEW_FILENAME
    completion = 0.0
    if interview_path.exists():
        interview = json.loads(interview_path.read_text())
        fields = interview.get("components", [])
        completion = _calculate_completion(answerset.get("data", {}), fields)

    return {**answerset, "completion_percentage": completion, "metadata": meta}


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_answerset(
    body: AnswersetCreate,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    templates_dir = _get_templates_dir(request)
    tenant_id = current_user.get("tenant_id")

    workgroup = None
    if body.workgroup_id:
        workgroup = get_workgroup_repository().get_by_id(body.workgroup_id)
        if not workgroup or workgroup.get("tenant_id") != tenant_id:
            raise HTTPException(status_code=404, detail="Workgroup not found")
        if current_user["role"] not in ("admin",):
            user_links = get_workgroup_user_repository().get_user_workgroups(current_user["id"])
            if body.workgroup_id not in {r["workgroup_id"] for r in user_links}:
                raise HTTPException(status_code=403, detail="Not a member of this workgroup")

    if not _user_has_template_access(body.template_id, current_user, tenant_id):
        raise HTTPException(status_code=403, detail="Template not available")

    submissions_dir = _get_submissions_dir(request, workgroup_id=body.workgroup_id)
    generated_dir = _get_generated_dir(request, workgroup_id=body.workgroup_id)

    template_dir = templates_dir / body.template_id
    tpl_path = template_dir / TEMPLATE_META_FILENAME
    if not tpl_path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    meta = json.loads(tpl_path.read_text())

    interview_path = template_dir / TEMPLATE_INTERVIEW_FILENAME
    if not interview_path.exists():
        raise HTTPException(status_code=500, detail="Template interview file not found")
    interview = json.loads(interview_path.read_text())
    fields = interview.get("components", [])

    try:
        validated_data = validate_submission_data(fields, body.data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    answerset_id = str(uuid.uuid4())
    now = utcnow_iso()
    requires_approval = bool(workgroup["requires_approval"]) if workgroup else False

    answerset = {
        "id": answerset_id,
        "template_id": body.template_id,
        "template_name": meta["name"],
        "interviewVersion": interview.get("version", 1),
        "data": validated_data,
        "context": body.context,
        "status": "pending",
        "workgroup_id": body.workgroup_id,
        "requires_approval": requires_approval,
        "submitted_by": current_user["id"],
        "submitted_by_name": current_user["name"],
        "submitted_at": now,
        "approved_by": None,
        "approved_at": None,
        "docx_path": None,
        "pdf_path": None,
    }

    try:
        docx_out, pdf_out = _generate_documents(meta, answerset, template_dir, generated_dir)
        answerset["docx_path"] = str(docx_out.relative_to(BACKEND_ROOT))
        answerset["pdf_path"] = str(pdf_out.relative_to(BACKEND_ROOT)) if pdf_out else None
        answerset["status"] = "generated"
    except Exception as e:
        answerset["status"] = "error"
        answerset["error"] = str(e)

    atomic_write_json(submissions_dir / f"{answerset_id}.json", answerset)

    metadata_entry = {
        "id": answerset_id,
        "template_id": body.template_id,
        "template_name": meta["name"],
        "interviewVersion": interview.get("version", 1),
        "context": body.context or "",
        "workgroup_id": body.workgroup_id,
        "submitted_by": current_user["id"],
        "submitted_by_name": current_user["name"],
        "submitted_at": now,
        "docx_path": answerset.get("docx_path"),
        "pdf_path": answerset.get("pdf_path"),
        "shared_with": [],
        "status": answerset["status"],
        "tenant_id": tenant_id,
        "version": 1,
    }
    get_answerset_metadata_repository().create(metadata_entry)
    _audit_log(request, answerset_id, "create", current_user)

    return answerset


@router.put("/{answerset_id}")
def update_answerset(
    answerset_id: str,
    body: AnswersetUpdate,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    meta_repo = get_answerset_metadata_repository()
    meta = meta_repo.get_by_id(answerset_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Answerset not found")

    _check_answerset_access(meta, current_user)

    if body.version != meta.get("version", 1):
        raise HTTPException(
            status_code=409,
            detail="Conflict: answerset has been modified by another user. Please refresh and try again.",
        )

    path = _find_answerset_file(request, answerset_id, workgroup_id=meta.get("workgroup_id"))
    answerset = json.loads(path.read_text())

    templates_dir = _get_templates_dir(request)
    template_dir = templates_dir / meta["template_id"]
    interview_path = template_dir / TEMPLATE_INTERVIEW_FILENAME
    if interview_path.exists():
        interview = json.loads(interview_path.read_text())
        fields = interview.get("components", [])
        try:
            validated_data = validate_submission_data(fields, body.data)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        validated_data = body.data

    answerset["data"] = validated_data
    if body.context is not None:
        answerset["context"] = body.context

    generated_dir = _get_generated_dir(request, workgroup_id=meta.get("workgroup_id"))
    try:
        tpl_path = template_dir / TEMPLATE_META_FILENAME
        if tpl_path.exists():
            tpl_meta = json.loads(tpl_path.read_text())
            docx_out, pdf_out = _generate_documents(tpl_meta, answerset, template_dir, generated_dir)
            answerset["docx_path"] = str(docx_out.relative_to(BACKEND_ROOT))
            answerset["pdf_path"] = str(pdf_out.relative_to(BACKEND_ROOT)) if pdf_out else None
            answerset["status"] = "generated"
    except Exception:
        pass

    atomic_write_json(path, answerset)

    new_version = meta.get("version", 1) + 1
    meta_repo.update(answerset_id, {
        "version": new_version,
        "context": answerset.get("context", ""),
        "docx_path": answerset.get("docx_path"),
        "pdf_path": answerset.get("pdf_path"),
        "status": answerset.get("status"),
    })

    _audit_log(request, answerset_id, "update", current_user, {"version": new_version})

    updated_meta = meta_repo.get_by_id(answerset_id)
    return {**answerset, "metadata": updated_meta}


@router.post("/{answerset_id}/clone", status_code=status.HTTP_201_CREATED)
def clone_answerset(
    answerset_id: str,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    meta_repo = get_answerset_metadata_repository()
    meta = meta_repo.get_by_id(answerset_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Answerset not found")

    _check_answerset_access(meta, current_user)

    path = _find_answerset_file(request, answerset_id, workgroup_id=meta.get("workgroup_id"))
    original = json.loads(path.read_text())

    new_id = str(uuid.uuid4())
    now = utcnow_iso()

    cloned = {**original}
    cloned["id"] = new_id
    cloned["submitted_by"] = current_user["id"]
    cloned["submitted_by_name"] = current_user["name"]
    cloned["submitted_at"] = now
    cloned["status"] = "pending"
    cloned["approved_by"] = None
    cloned["approved_at"] = None
    cloned["docx_path"] = None
    cloned["pdf_path"] = None
    cloned["workgroup_id"] = meta.get("workgroup_id")

    submissions_dir = _get_submissions_dir(request, workgroup_id=meta.get("workgroup_id"))
    atomic_write_json(submissions_dir / f"{new_id}.json", cloned)

    new_meta = {
        "id": new_id,
        "template_id": meta["template_id"],
        "template_name": meta["template_name"],
        "interviewVersion": meta.get("interviewVersion", 1),
        "context": meta.get("context", ""),
        "workgroup_id": meta.get("workgroup_id"),
        "submitted_by": current_user["id"],
        "submitted_by_name": current_user["name"],
        "submitted_at": now,
        "docx_path": None,
        "pdf_path": None,
        "shared_with": [],
        "status": "pending",
        "tenant_id": current_user.get("tenant_id"),
        "version": 1,
        "cloned_from": answerset_id,
    }
    meta_repo.create(new_meta)
    _audit_log(request, answerset_id, "clone", current_user, {"new_id": new_id})
    _audit_log(request, new_id, "create", current_user, {"cloned_from": answerset_id})

    return cloned


@router.put("/{answerset_id}/share")
def share_answerset(
    answerset_id: str,
    body: AnswersetShare,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    meta_repo = get_answerset_metadata_repository()
    meta = meta_repo.get_by_id(answerset_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Answerset not found")

    if meta.get("submitted_by") != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only the owner or admin can share this answerset")

    if meta.get("workgroup_id"):
        raise HTTPException(status_code=400, detail="Workitem answersets inherit access from workgroup membership")

    meta_repo.update(answerset_id, {"shared_with": body.shared_with})
    _audit_log(request, answerset_id, "share", current_user, {"shared_with": body.shared_with})

    return meta_repo.get_by_id(answerset_id)


@router.post("/{answerset_id}/generate")
def generate_answerset_documents(
    answerset_id: str,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    meta_repo = get_answerset_metadata_repository()
    meta = meta_repo.get_by_id(answerset_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Answerset not found")

    _check_answerset_access(meta, current_user)

    path = _find_answerset_file(request, answerset_id, workgroup_id=meta.get("workgroup_id"))
    answerset = json.loads(path.read_text())

    templates_dir = _get_templates_dir(request)
    template_dir = templates_dir / meta["template_id"]
    tpl_path = template_dir / TEMPLATE_META_FILENAME
    if not tpl_path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    tpl_meta = json.loads(tpl_path.read_text())

    generated_dir = _get_generated_dir(request, workgroup_id=meta.get("workgroup_id"))

    try:
        docx_out, pdf_out = _generate_documents(tpl_meta, answerset, template_dir, generated_dir)
        answerset["docx_path"] = str(docx_out.relative_to(BACKEND_ROOT))
        answerset["pdf_path"] = str(pdf_out.relative_to(BACKEND_ROOT)) if pdf_out else None
        answerset["status"] = "generated"
    except Exception as e:
        answerset["status"] = "error"
        answerset["error"] = str(e)
        atomic_write_json(path, answerset)
        raise HTTPException(status_code=500, detail=str(e))

    atomic_write_json(path, answerset)
    meta_repo.update(answerset_id, {
        "docx_path": answerset.get("docx_path"),
        "pdf_path": answerset.get("pdf_path"),
        "status": answerset["status"],
    })
    _audit_log(request, answerset_id, "generate", current_user)

    return answerset


@router.get("/{answerset_id}/download/{format}")
def download_answerset_document(
    answerset_id: str,
    format: str,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    if format not in ("docx", "pdf"):
        raise HTTPException(status_code=400, detail="Format must be docx or pdf")

    meta_repo = get_answerset_metadata_repository()
    meta = meta_repo.get_by_id(answerset_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Answerset not found")

    _check_answerset_access(meta, current_user)

    path = _find_answerset_file(request, answerset_id, workgroup_id=meta.get("workgroup_id"))
    answerset = json.loads(path.read_text())

    file_path_key = f"{format}_path"
    rel_path = answerset.get(file_path_key)
    if not rel_path:
        raise HTTPException(status_code=404, detail=f"{format.upper()} file not available")

    from fastapi.responses import FileResponse

    file_path = BACKEND_ROOT / rel_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"{format.upper()} file not available")

    _audit_log(request, answerset_id, "download", current_user, {"format": format})

    media_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if format == "docx"
        else "application/pdf"
    )
    filename = f"{answerset['template_name'].replace(' ', '_')}_{answerset_id[:8]}.{format}"
    return FileResponse(str(file_path), media_type=media_type, filename=filename)


@router.delete("/{answerset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_answerset(
    answerset_id: str,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    meta_repo = get_answerset_metadata_repository()
    meta = meta_repo.get_by_id(answerset_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Answerset not found")

    if meta.get("submitted_by") != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only the owner or admin can delete this answerset")

    try:
        path = _find_answerset_file(request, answerset_id, workgroup_id=meta.get("workgroup_id"))
        path.unlink(missing_ok=True)
    except HTTPException:
        pass

    meta_repo.delete(answerset_id)
    _audit_log(request, answerset_id, "delete", current_user)


@router.get("/{answerset_id}/audit")
def get_answerset_audit(
    answerset_id: str,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    if current_user["role"] not in ("admin", "approver"):
        raise HTTPException(status_code=403, detail="Not permitted")

    meta_repo = get_answerset_metadata_repository()
    meta = meta_repo.get_by_id(answerset_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Answerset not found")

    audit_repo = get_audit_log_repository()
    return audit_repo.get_by_answerset(answerset_id)
