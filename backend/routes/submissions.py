import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import json, uuid, subprocess, shutil
from pathlib import Path
from docxtpl import DocxTemplate
from auth_utils import get_current_user, require_role
from question_schema import validate_submission_data
from tenant_context import get_current_tenant, is_tenant_subdomain, verify_tenant_match
from file_utils import (
    BACKEND_ROOT,
    TEMPLATE_META_FILENAME,
    TEMPLATE_INTERVIEW_FILENAME,
    TEMPLATE_DOCX_FILENAME,
    get_tenant_data_dir,
    get_workgroup_subdir,
    atomic_write_json,
    utcnow_iso,
)
from repositories.factory import (
    get_template_settings_repository,
    get_workgroup_repository,
    get_workgroup_template_repository,
    get_workgroup_user_repository,
)

router = APIRouter()


def get_submissions_dir(request: Request, workgroup_id: Optional[str] = None) -> Path:
    base = get_tenant_data_dir(request, "data", "submissions")
    if workgroup_id:
        return get_workgroup_subdir(base, workgroup_id)
    return base


def get_templates_dir(request: Request) -> Path:
    return get_tenant_data_dir(request, "data", "templates")


def get_generated_dir(request: Request, workgroup_id: Optional[str] = None) -> Path:
    base = get_tenant_data_dir(request, "uploads", "generated")
    if workgroup_id:
        return get_workgroup_subdir(base, workgroup_id)
    return base


def read_submissions(
    submissions_dir: Path,
    filter_template: str = None,
    filter_user: str = None,
    role: str = None,
    workgroup_id: Optional[str] = None,
) -> list:
    if workgroup_id:
        submissions_dir = submissions_dir / "workgroups" / workgroup_id
        if not submissions_dir.exists():
            return []
    out = []
    for f in submissions_dir.glob("*.json"):
        try:
            s = json.loads(f.read_text())
            if filter_template and s.get("template_id") != filter_template:
                continue
            if role == "staff" and filter_user and s.get("submitted_by") != filter_user:
                continue
            out.append(s)
        except Exception:
            pass
    return sorted(out, key=lambda x: x.get("submitted_at", ""), reverse=True)


class SubmissionCreate(BaseModel):
    template_id: str
    data: dict
    context: Optional[str] = ""
    workgroup_id: Optional[str] = None


@router.get("/")
def list_submissions(
    request: Request,
    template_id: Optional[str] = None,
    workgroup_id: Optional[str] = None,
    current_user: dict = Depends(verify_tenant_match),
):
    submissions_dir = get_submissions_dir(request)
    user_id = current_user["id"] if current_user["role"] == "staff" else None
    return read_submissions(
        submissions_dir,
        filter_template=template_id,
        filter_user=user_id,
        role=current_user["role"],
        workgroup_id=workgroup_id,
    )


def _find_submission_path(
    request: Request, submission_id: str
) -> tuple[Path, Optional[str]]:
    """Locate a submission JSON file. Returns (path, workgroup_id)."""
    base = get_submissions_dir(request)
    root_path = base / f"{submission_id}.json"
    if root_path.exists():
        return root_path, None
    workgroups_root = base / "workgroups"
    if workgroups_root.exists():
        for wg_dir in workgroups_root.iterdir():
            if not wg_dir.is_dir():
                continue
            candidate = wg_dir / f"{submission_id}.json"
            if candidate.exists():
                return candidate, wg_dir.name
    raise HTTPException(status_code=404, detail="Submission not found")


@router.get("/{submission_id}")
def get_submission(submission_id: str, request: Request, current_user: dict = Depends(verify_tenant_match)):
    path, _ = _find_submission_path(request, submission_id)
    sub = json.loads(path.read_text())
    if current_user["role"] == "staff" and sub["submitted_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return sub


def _user_has_template_access(
    template_id: str,
    current_user: dict,
    tenant_id: Optional[str],
) -> bool:
    """Apply workgroup-based template visibility rules.

    Returns True when the user is allowed to use *template_id*. Admins can
    always access tenant templates; staff/approvers are restricted to
    workgroup-allowed templates when ``restricted_to_workgroups`` is enabled.
    """
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


@router.post("/")
def create_submission(
    body: SubmissionCreate,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    templates_dir = get_templates_dir(request)

    workgroup = None
    if body.workgroup_id:
        workgroup = get_workgroup_repository().get_by_id(body.workgroup_id)
        if not workgroup or workgroup.get("tenant_id") != current_user.get("tenant_id"):
            raise HTTPException(status_code=404, detail="Workgroup not found")
        if current_user["role"] not in ("admin",):
            user_links = get_workgroup_user_repository().get_user_workgroups(current_user["id"])
            if body.workgroup_id not in {r["workgroup_id"] for r in user_links}:
                raise HTTPException(status_code=403, detail="Not a member of this workgroup")

    if not _user_has_template_access(
        body.template_id, current_user, current_user.get("tenant_id")
    ):
        raise HTTPException(status_code=403, detail="Template not available")

    submissions_dir = get_submissions_dir(request, workgroup_id=body.workgroup_id)
    generated_dir = get_generated_dir(request, workgroup_id=body.workgroup_id)

    # Per-template subdirectory layout (#8)
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

    submission_id = str(uuid.uuid4())
    now = utcnow_iso()

    requires_approval = bool(workgroup["requires_approval"]) if workgroup else False

    # Store interview version for traceability (#4)
    submission = {
        "id": submission_id,
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
        docx_out, pdf_out = generate_documents(meta, submission, template_dir, generated_dir)
        # Store paths relative to BACKEND_ROOT (#3)
        submission["docx_path"] = str(docx_out.relative_to(BACKEND_ROOT))
        submission["pdf_path"] = str(pdf_out.relative_to(BACKEND_ROOT)) if pdf_out else None
        submission["status"] = "generated"
    except Exception as e:
        submission["status"] = "error"
        submission["error"] = str(e)

    atomic_write_json(submissions_dir / f"{submission_id}.json", submission)

    # submissionCount is now derived, no need to update meta (#1)

    return submission


def generate_documents(template: dict, submission: dict, template_dir: Path, generated_dir: Path):
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
            capture_output=True, timeout=30
        )
        if result.returncode != 0:
            pdf_out = None
    else:
        pdf_out = None

    return docx_out, pdf_out


@router.put("/{submission_id}/approve")
def approve_submission(
    submission_id: str,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    if current_user["role"] not in ("admin", "approver"):
        raise HTTPException(status_code=403, detail="Not permitted")
    path, _ = _find_submission_path(request, submission_id)
    sub = json.loads(path.read_text())
    wg_id = sub.get("workgroup_id")
    if wg_id:
        wg = get_workgroup_repository().get_by_id(wg_id)
        if wg and not wg.get("requires_approval"):
            sub["requires_approval"] = False
    sub["status"] = "approved"
    sub["approved_by"] = current_user["id"]
    sub["approved_by_name"] = current_user["name"]
    sub["approved_at"] = utcnow_iso()
    atomic_write_json(path, sub)
    return sub


@router.put("/{submission_id}/reject")
def reject_submission(
    submission_id: str,
    body: dict,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    if current_user["role"] not in ("admin", "approver"):
        raise HTTPException(status_code=403, detail="Not permitted")
    path, _ = _find_submission_path(request, submission_id)
    sub = json.loads(path.read_text())
    sub["status"] = "rejected"
    sub["rejection_reason"] = body.get("reason", "")
    sub["rejected_by"] = current_user["id"]
    sub["rejected_at"] = utcnow_iso()
    atomic_write_json(path, sub)
    return sub


@router.get("/{submission_id}/download/{format}")
def download_document(
    submission_id: str,
    format: str,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    if format not in ("docx", "pdf"):
        raise HTTPException(status_code=400, detail="Format must be docx or pdf")

    path, _ = _find_submission_path(request, submission_id)
    sub = json.loads(path.read_text())

    if current_user["role"] == "staff" and sub["submitted_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    file_path_key = f"{format}_path"
    rel_path = sub.get(file_path_key)
    if not rel_path:
        raise HTTPException(status_code=404, detail=f"{format.upper()} file not available")

    # Resolve relative path back to absolute (#3)
    file_path = BACKEND_ROOT / rel_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"{format.upper()} file not available")

    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if format == "docx" else "application/pdf"
    filename = f"{sub['template_name'].replace(' ', '_')}_{submission_id[:8]}.{format}"
    return FileResponse(str(file_path), media_type=media_type, filename=filename)
