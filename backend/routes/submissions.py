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
from expression_eval import evaluate_expression
from tenant_context import get_current_tenant, is_tenant_subdomain, verify_tenant_match
from file_utils import (
    BACKEND_ROOT,
    TEMPLATE_META_FILENAME,
    TEMPLATE_INTERVIEW_FILENAME,
    TEMPLATE_DOCX_FILENAME,
    get_tenant_data_dir,
    atomic_write_json,
    utcnow_iso,
)

router = APIRouter()


def _recompute_expressions(components: list, data: dict) -> dict:
    """Evaluate all expression fields and inject computed values into data.

    Walks the component tree and evaluates number fields with ``expression``.
    Repeat-group children are skipped (their values come from the frontend).
    Returns a new dict with computed values added.
    """
    result = dict(data)
    for comp in components:
        ctype = comp.get("type", "")
        if ctype == "dialog":
            result = _recompute_expressions(comp.get("components", []), result)
        elif ctype == "number" and comp.get("expression"):
            val = evaluate_expression(comp["expression"], result)
            if val is not None:
                dp = comp.get("decimalPlaces")
                result[comp["id"]] = round(val, dp) if dp is not None else val
    return result


def get_submissions_dir(request: Request) -> Path:
    return get_tenant_data_dir(request, "data", "submissions")


def get_templates_dir(request: Request) -> Path:
    return get_tenant_data_dir(request, "data", "templates")


def get_generated_dir(request: Request) -> Path:
    return get_tenant_data_dir(request, "uploads", "generated")


def read_submissions(submissions_dir: Path, filter_template: str = None, filter_user: str = None, role: str = None) -> list:
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


@router.get("/")
def list_submissions(
    request: Request,
    template_id: Optional[str] = None,
    current_user: dict = Depends(verify_tenant_match),
):
    submissions_dir = get_submissions_dir(request)
    user_id = current_user["id"] if current_user["role"] == "staff" else None
    return read_submissions(submissions_dir, filter_template=template_id, filter_user=user_id, role=current_user["role"])


@router.get("/{submission_id}")
def get_submission(submission_id: str, request: Request, current_user: dict = Depends(verify_tenant_match)):
    submissions_dir = get_submissions_dir(request)
    path = submissions_dir / f"{submission_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Submission not found")
    sub = json.loads(path.read_text())
    if current_user["role"] == "staff" and sub["submitted_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return sub


@router.post("/")
def create_submission(
    body: SubmissionCreate,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    templates_dir = get_templates_dir(request)
    submissions_dir = get_submissions_dir(request)
    generated_dir = get_generated_dir(request)

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

    # Evaluate computed expression fields before rendering
    validated_data = _recompute_expressions(fields, validated_data)

    submission_id = str(uuid.uuid4())
    now = utcnow_iso()

    # Store interview version for traceability (#4)
    submission = {
        "id": submission_id,
        "template_id": body.template_id,
        "template_name": meta["name"],
        "interviewVersion": interview.get("version", 1),
        "data": validated_data,
        "context": body.context,
        "status": "pending",
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
    if current_user["role"] not in ("admin", "approver", "superadmin"):
        raise HTTPException(status_code=403, detail="Not permitted")
    submissions_dir = get_submissions_dir(request)
    path = submissions_dir / f"{submission_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Submission not found")
    sub = json.loads(path.read_text())
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
    if current_user["role"] not in ("admin", "approver", "superadmin"):
        raise HTTPException(status_code=403, detail="Not permitted")
    submissions_dir = get_submissions_dir(request)
    path = submissions_dir / f"{submission_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Submission not found")
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

    submissions_dir = get_submissions_dir(request)
    path = submissions_dir / f"{submission_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Submission not found")
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
