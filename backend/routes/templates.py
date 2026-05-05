import sys, os
import logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Form
from pydantic import BaseModel
from typing import Optional, List
import json, uuid, re, zipfile,base64
from pathlib import Path
from datetime import datetime
from fastapi import HTTPException, APIRouter, Request
from fastapi.responses import FileResponse
from typing import Optional
from auth_utils import get_current_user, require_role
from question_schema import validate_questions
from config import settings
from AiResponseSaver import AiResponseSaver
from datetime import datetime
from tenant_context import get_current_tenant, is_tenant_subdomain, verify_tenant_match

from prompts.promptbuilder import _build_system_prompt
import providers  # noqa: F401 — triggers provider self-registration  
from ai_providers import get_provider

BACKEND_ROOT = Path(__file__).resolve().parent.parent  
SCHEMA_DIR = BACKEND_ROOT / "schema"  
  
# Map provider name → schema file  
PROVIDER_SCHEMA = {  
    "devin":  "AiResponseSchemaFile.json",  
    "gemini": "AiResponseSchema.json",  
} 

router = APIRouter()

TEMPLATES_DATA = BACKEND_ROOT / "data" / "templates"  

TEMPLATES_UPLOAD = Path("uploads/templates")

OPENAI_SYSTEM_PROMPT = _build_system_prompt()


def get_templates_dir(request: Request) -> Path:
    if not is_tenant_subdomain(request):
        raise HTTPException(status_code=403, detail="Templates are tenant-scoped")
    tenant = get_current_tenant(request)
    if not tenant:
        raise HTTPException(status_code=403, detail="Templates are tenant-scoped")
    path = BACKEND_ROOT / "data" / "templates" / tenant["id"]
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_template_with_interview(meta_path: Path, templates_dir: Path) -> dict:
    """Load a template meta file and merge its associated interview components."""
    meta = json.loads(meta_path.read_text())
    interview_path = templates_dir / meta.get("interviewFile", "")
    if interview_path.exists():
        interview = json.loads(interview_path.read_text())
        meta["fields"] = interview.get("components", [])
        meta["rules"] = interview.get("rules", [])
    else:
        meta["fields"] = []
        meta["rules"] = []
    return meta


def read_templates(templates_dir: Path) -> list:
    out = []
    for f in templates_dir.glob("*_meta.json"):
        try:
            out.append(_load_template_with_interview(f, templates_dir))
        except Exception:
            pass
    return sorted(out, key=lambda x: x.get("createdAt", x.get("created_at", "")), reverse=True)


def extract_placeholders_from_docx(path: Path) -> List[str]:
    """Extract {{placeholder}} tags from a docx file."""
    placeholders = set()
    try:
        with zipfile.ZipFile(path, "r") as z:
            for name in z.namelist():
                if name.endswith(".xml"):
                    text = z.read(name).decode("utf-8", errors="ignore")
                    found = re.findall(r'\{\{([^}]+)\}\}', text)
                    placeholders.update(f.strip() for f in found)
    except Exception as e:
        pass
    return sorted(placeholders)


@router.get("/ai-status")  
def ai_status(current_user: dict = Depends(verify_tenant_match)):  
    provider_name = os.environ.get("AI_PROVIDER", "devin")  
    try:  
        get_provider(provider_name, system_prompt=OPENAI_SYSTEM_PROMPT)  
        return {"available": True}  
    except Exception:  
        return {"available": False}


@router.get("/")
def list_templates(request: Request, current_user: dict = Depends(verify_tenant_match)):
    templates_dir = get_templates_dir(request)
    return read_templates(templates_dir)


@router.get("/{template_id}")
def get_template(template_id: str, request: Request, current_user: dict = Depends(verify_tenant_match)):
    templates_dir = get_templates_dir(request)
    path = templates_dir / f"{template_id}_meta.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    return _load_template_with_interview(path, templates_dir)


@router.post("/")
async def create_template(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
    interview_json: Optional[str] = Form(None),
    current_user: dict = Depends(verify_tenant_match),
):
    if current_user["role"] not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Not permitted")
    templates_dir = get_templates_dir(request)

    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")

    template_id = str(uuid.uuid4())
    filename = f"{template_id}.docx"
    upload_path = templates_dir / filename

    content = await file.read()
    upload_path.write_bytes(content)

    if interview_json:
        try:
            parsed = json.loads(interview_json)
        except json.JSONDecodeError as e:
            upload_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=f"Invalid interview JSON: {e}")

        if isinstance(parsed, dict) and "components" in parsed:
            interview = parsed
        elif isinstance(parsed, list):
            interview = {
                "$schema": "https://github.com/danrocks/docform/blob/master/backend/schema/InterviewSchema.json",
                "schemaVersion": 1,
                "id": f"{template_id}_interview",
                "version": 1,
                "title": name,
                "description": description,
                "components": parsed,
            }
        else:
            upload_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="Invalid interview JSON: expected object with 'components' or a list of components")

        try:
            validate_questions(interview.get("components", []))
        except ValueError as e:
            upload_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=str(e))
    else:
        placeholders = extract_placeholders_from_docx(upload_path)
        interview = {
            "$schema": "https://github.com/danrocks/docform/blob/master/backend/schema/InterviewSchema.json",
            "schemaVersion": 1,
            "id": f"{template_id}_interview",
            "version": 1,
            "title": name,
            "description": description,
            "components": [
                {
                    "type": "string",
                    "id": p,
                    "label": p.replace("_", " ").title(),
                    "required": True,
                    "maxLength": 500,
                }
                for p in placeholders
            ],
        }

    interview_filename = f"{template_id}_interview.json"
    (templates_dir / interview_filename).write_text(json.dumps(interview, indent=2))

    meta = {
        "$schema": "https://github.com/danrocks/docform/blob/master/backend/schema/TemplateMetaSchema.json",
        "schemaVersion": 1,
        "id": template_id,
        "name": name,
        "description": description,
        "interviewFile": interview_filename,
        "documentFile": filename,
        "originalFilename": file.filename,
        "active": True,
        "createdAt": datetime.utcnow().isoformat(),
        "createdBy": current_user["id"],
        "updatedAt": None,
        "submissionCount": 0,
        "generationMethod": "upload",
    }

    meta_path = templates_dir / f"{template_id}_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2))
    return _load_template_with_interview(meta_path, templates_dir)


@router.put("/{template_id}")
def update_template(
    template_id: str,
    body: dict,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    if current_user["role"] not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Not permitted")
    templates_dir = get_templates_dir(request)
    path = templates_dir / f"{template_id}_meta.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    meta = json.loads(path.read_text())

    allowed_meta = {"name", "description", "active"}
    for k, v in body.items():
        if k in allowed_meta:
            meta[k] = v

    if "fields" in body:
        try:
            components = validate_questions(body["fields"])
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        interview_path = templates_dir / meta.get("interviewFile", f"{template_id}_interview.json")
        if interview_path.exists():
            interview = json.loads(interview_path.read_text())
        else:
            interview = {
                "$schema": "https://github.com/danrocks/docform/blob/master/backend/schema/InterviewSchema.json",
                "schemaVersion": 1,
                "id": f"{template_id}_interview",
                "version": 1,
                "title": meta.get("name", ""),
                "description": meta.get("description", ""),
            }
        interview["components"] = components
        interview_path.write_text(json.dumps(interview, indent=2))

    meta["updatedAt"] = datetime.utcnow().isoformat()
    path.write_text(json.dumps(meta, indent=2))
    return _load_template_with_interview(path, templates_dir)


@router.delete("/{template_id}")
def delete_template(
    template_id: str,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    if current_user["role"] not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Not permitted")
    templates_dir = get_templates_dir(request)
    path = templates_dir / f"{template_id}_meta.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    meta = json.loads(path.read_text())
    docx_path = templates_dir / meta.get("documentFile", "")
    interview_path = templates_dir / meta.get("interviewFile", "")
    if docx_path.exists():
        docx_path.unlink()
    if interview_path.exists():
        interview_path.unlink()
    path.unlink()
    return {"detail": "Deleted"}


class GenerateRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    prompt: str


class RegenerateRequest(BaseModel):
    prompt: str


def _create_docx_from_content(document_content: str, output_path: Path):
    """Create a .docx file from AI-generated document content."""
    from docx import Document
    doc = Document()
    lines = document_content.split("\n")
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            doc.add_heading(stripped[2:], level=1)
        elif stripped.startswith("## "):
            doc.add_heading(stripped[3:], level=2)
        elif stripped.startswith("### "):
            doc.add_heading(stripped[4:], level=3)
        elif stripped.isupper() and len(stripped) > 3 and not stripped.startswith("{{"):
            doc.add_heading(stripped, level=1)
        else:
            doc.add_paragraph(stripped)
    doc.save(str(output_path))


def _call_ai(prompt: str, model: str | None = None, tenant_id: str | None = None) -> dict:  
    provider_name = os.environ.get("AI_PROVIDER", "devin")  
    provider = get_provider(provider_name, system_prompt=OPENAI_SYSTEM_PROMPT)  
    kwargs = {}  
    if model:  
        kwargs["model"] = model  
    if tenant_id:
        kwargs["tenant_id"] = tenant_id
    return provider.call(prompt, **kwargs)

def _get_provider_format() -> str | None:  
    """Read the document format from the provider's schema file."""  
    provider_name = os.environ.get("AI_PROVIDER", "devin")  
    schema_file = PROVIDER_SCHEMA.get(provider_name)  
    if not schema_file:  
        return None  
    schema_path = SCHEMA_DIR / schema_file  
    if not schema_path.exists():  
        return None  
    schema = json.loads(schema_path.read_text())  
    return schema.get("properties", {}).get("document", {}).get("format")


@router.post("/generate")  
def generate_template(  
    request: Request,
    body: GenerateRequest,  
    current_user: dict = Depends(verify_tenant_match),
):  
    if current_user["role"] not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Not permitted")
    templates_dir = get_templates_dir(request)
    templates_dir.mkdir(parents=True, exist_ok=True)  
  
    tenant = get_current_tenant(request)
    ai_result = _call_ai(body.prompt, tenant_id=tenant["id"] if tenant else None)
  
    fmt = _get_provider_format()

    template_id = str(uuid.uuid4())  
    filename = f"{template_id}.docx"  
    upload_path = templates_dir / filename  
  
    if fmt == "url":
        import httpx as _httpx

        doc_url = ai_result.get("document", "")
        int_url = ai_result.get("interview", "")
        if not doc_url or not int_url:
            raise HTTPException(status_code=500, detail="AI did not return document/interview URLs")

        # Get API key for authenticated downloads
        devin_key = os.environ.get("DEVIN_KEY", getattr(settings, "DEVIN_KEY", None))
        download_headers = {}
        if devin_key:
            download_headers["Authorization"] = f"Bearer {devin_key}"

        max_retries = 3

        # Download document with retries
        doc_resp = None
        for attempt in range(max_retries):
            try:
                doc_resp = _httpx.get(doc_url, follow_redirects=True, timeout=60, headers=download_headers)
                doc_resp.raise_for_status()
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise HTTPException(status_code=502, detail=f"Failed to download document from {doc_url} after {max_retries} attempts: {e}")
                import time
                time.sleep(2 ** attempt)  # exponential backoff: 1s, 2s, 4s

        upload_path.write_bytes(doc_resp.content)

        # Download interview with retries
        int_resp = None
        for attempt in range(max_retries):
            try:
                int_resp = _httpx.get(int_url, follow_redirects=True, timeout=60, headers=download_headers)
                int_resp.raise_for_status()
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise HTTPException(status_code=502, detail=f"Failed to download interview from {int_url} after {max_retries} attempts: {e}")
                import time
                time.sleep(2 ** attempt)

        interview_data = int_resp.json()

        if isinstance(interview_data, dict):
            raw_questions = interview_data.get("components", interview_data.get("questions", []))
        elif isinstance(interview_data, list):
            raw_questions = interview_data
        else:
            raise HTTPException(status_code=500, detail="Unexpected interview format")

    elif fmt == "base64":  
        doc_b64 = ai_result.get("document", "")  
        int_b64 = ai_result.get("interview", "")  
        if not doc_b64 or not int_b64:  
            raise HTTPException(status_code=500, detail="AI did not return document/interview content")  
  
        try:  
            upload_path.write_bytes(base64.b64decode(doc_b64))  
        except Exception as e:  
            raise HTTPException(status_code=500, detail=f"Failed to decode document: {e}")  
  
        try:  
            interview_text = base64.b64decode(int_b64).decode("utf-8")  
            interview_data = json.loads(interview_text)  
        except Exception as e:  
            raise HTTPException(status_code=500, detail=f"Failed to decode interview: {e}")  
  
        if isinstance(interview_data, dict):
            raw_questions = interview_data.get("components", interview_data.get("questions", []))
        elif isinstance(interview_data, list):
            raw_questions = interview_data
        else:
            raise HTTPException(status_code=500, detail="Unexpected interview format")

    else:
        document_content = ai_result.get("document_content", "")
        raw_questions = ai_result.get("questions", [])
        interview_data = None
        if not document_content:
            raise HTTPException(status_code=500, detail="AI did not generate document content")
        try:
            _create_docx_from_content(document_content, upload_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create document: {e}")
  
    if not raw_questions:  
        raise HTTPException(status_code=500, detail="AI did not generate interview questions")  
  
    try:
        fields = validate_questions(raw_questions)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"AI generated invalid questions: {e}")

    description = body.description or ai_result.get("summary", "")

    if isinstance(interview_data, dict) and "components" in interview_data:
        interview = interview_data
        interview["components"] = fields
    else:
        interview = {
            "$schema": "https://github.com/danrocks/docform/blob/master/backend/schema/InterviewSchema.json",
            "schemaVersion": 1,
            "id": f"{template_id}_interview",
            "version": 1,
            "title": body.name,
            "description": description,
            "components": fields,
        }

    interview_filename = f"{template_id}_interview.json"
    (templates_dir / interview_filename).write_text(json.dumps(interview, indent=2))

    meta = {
        "$schema": "https://github.com/danrocks/docform/blob/master/backend/schema/TemplateMetaSchema.json",
        "schemaVersion": 1,
        "id": template_id,
        "name": body.name,
        "description": description,
        "interviewFile": interview_filename,
        "documentFile": filename,
        "originalFilename": f"{body.name.replace(' ', '_')}.docx",
        "active": True,
        "createdAt": datetime.utcnow().isoformat(),
        "createdBy": current_user["id"],
        "updatedAt": None,
        "submissionCount": 0,
        "generationMethod": "ai",
        "originalPrompt": body.prompt,
    }

    meta_path = templates_dir / f"{template_id}_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2))
    return _load_template_with_interview(meta_path, templates_dir)

@router.post("/{template_id}/regenerate")
def regenerate_template(
    template_id: str,
    body: RegenerateRequest,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    if current_user["role"] not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Not permitted")
    templates_dir = get_templates_dir(request)
    path = templates_dir / f"{template_id}_meta.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Template not found")

    api_key = os.environ.get("OPENAI_API_KEY", settings.OPENAI_API_KEY)
    if not api_key:
        raise HTTPException(status_code=501, detail="AI generation not configured")

    model = os.environ.get("OPENAI_MODEL", "gpt-4o")
    meta = json.loads(path.read_text())

    ai_result = _call_ai(body.prompt, model)

    document_content = ai_result.get("document_content", "")
    raw_questions = ai_result.get("questions", [])

    if not document_content:
        raise HTTPException(status_code=500, detail="AI did not generate document content")
    if not raw_questions:
        raise HTTPException(status_code=500, detail="AI did not generate interview questions")

    try:
        fields = validate_questions(raw_questions)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"AI generated invalid questions: {e}")

    upload_path = templates_dir / meta["documentFile"]
    try:
        _create_docx_from_content(document_content, upload_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create document: {e}")

    interview_filename = meta.get("interviewFile", f"{template_id}_interview.json")
    interview_path = templates_dir / interview_filename
    if interview_path.exists():
        interview = json.loads(interview_path.read_text())
    else:
        interview = {
            "$schema": "https://github.com/danrocks/docform/blob/master/backend/schema/InterviewSchema.json",
            "schemaVersion": 1,
            "id": f"{template_id}_interview",
            "version": 1,
            "title": meta.get("name", ""),
            "description": meta.get("description", ""),
        }
    interview["components"] = fields
    interview_path.write_text(json.dumps(interview, indent=2))

    meta["interviewFile"] = interview_filename
    meta["originalPrompt"] = body.prompt
    meta["generationMethod"] = "ai"
    meta["updatedAt"] = datetime.utcnow().isoformat()

    path.write_text(json.dumps(meta, indent=2))
    return _load_template_with_interview(path, templates_dir)

# New route to serve generated files safely
@router.get("/download/{filename}")
def download_generated_file(
    filename: str,
    request: Request,
    current_user: dict = Depends(verify_tenant_match),
):
    if not re.match(r"^[\w\-. ]+\.(json|docx)$", filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    templates_dir = get_templates_dir(request)
    file_path = os.path.abspath(os.path.join(str(templates_dir), filename))
    if not file_path.startswith(str(templates_dir.resolve()) + os.sep):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=filename, media_type="application/octet-stream")
