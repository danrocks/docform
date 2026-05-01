import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import json, uuid, subprocess, shutil
from pathlib import Path
from datetime import datetime
from docxtpl import DocxTemplate
from auth_utils import get_current_user, require_role
from question_schema import validate_submission_data
from tenant_context import get_current_tenant, is_tenant_subdomain, verify_tenant_match

router = APIRouter()

BACKEND_ROOT = Path(__file__).resolve().parent.parent


def get_submissions_dir(request: Request) -> Path:
    if not is_tenant_subdomain(request):
        raise HTTPException(status_code=403, detail="Submissions are tenant-scoped")
    tenant = get_current_tenant(request)
    if not tenant:
        raise HTTPException(status_code=403, detail="Submissions are tenant-scoped")
    path = BACKEND_ROOT / "data" / "submissions" / tenant["id"]
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_templates_dir(request: Request) -> Path:
    if not is_tenant_subdomain(request):
        raise HTTPException(status_code=403, detail="Templates are tenant-scoped")
    tenant = get_current_tenant(request)
    if not tenant:
        raise HTTPException(status_code=403, detail="Templates are tenant-scoped")
    path = BACKEND_ROOT / "data" / "templates" / tenant["id"]
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_generated_dir(request: Request) -> Path:
    if not is_tenant_subdomain(request):
        raise HTTPException(status_code=403, detail="Submissions are tenant-scoped")
    tenant = get_current_tenant(request)
    if not tenant:
        raise HTTPException(status_code=403, detail="Submissions are tenant-scoped")
    path = BACKEND_ROOT / "uploads" / "generated" / tenant["id"]
    path.mkdir(parents=True, exist_ok=True)
    return path


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

    tpl_path = templates_dir / f"{body.template_id}_meta.json"
    if not tpl_path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    meta = json.loads(tpl_path.read_text())

    interview_path = templates_dir / meta.get("interviewFile", "")
    if not interview_path.exists():
        raise HTTPException(status_code=500, detail="Template interview file not found")
    interview = json.loads(interview_path.read_text())
    fields = interview.get("components", [])

    try:
        validated_data = validate_submission_data(fields, body.data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    submission_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    submission = {
        "id": submission_id,
        "template_id": body.template_id,
        "template_name": meta["name"],
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
        docx_out, pdf_out = generate_documents(meta, submission, templates_dir, generated_dir)
        submission["docx_path"] = str(docx_out)
        submission["pdf_path"] = str(pdf_out) if pdf_out else None
        submission["status"] = "generated"
    except Exception as e:
        submission["status"] = "error"
        submission["error"] = str(e)

    (submissions_dir / f"{submission_id}.json").write_text(json.dumps(submission, indent=2))

    meta["submissionCount"] = meta.get("submissionCount", 0) + 1
    tpl_path.write_text(json.dumps(meta, indent=2))

    return submission


def generate_documents(template: dict, submission: dict, templates_dir: Path, generated_dir: Path):
    """Fill the docx template and convert to PDF."""
    generated_dir.mkdir(parents=True, exist_ok=True)
    src = templates_dir / template["documentFile"]
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
    sub["approved_at"] = datetime.utcnow().isoformat()
    path.write_text(json.dumps(sub, indent=2))
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
    sub["rejected_at"] = datetime.utcnow().isoformat()
    path.write_text(json.dumps(sub, indent=2))
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
    file_path = sub.get(file_path_key)
    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail=f"{format.upper()} file not available")

    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if format == "docx" else "application/pdf"
    filename = f"{sub['template_name'].replace(' ', '_')}_{submission_id[:8]}.{format}"
    return FileResponse(file_path, media_type=media_type, filename=filename)
