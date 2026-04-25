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

TEMPLATES_DATA = Path("data/templates")
TEMPLATES_UPLOAD = Path("uploads/templates")

OPENAI_SYSTEM_PROMPT = _build_system_prompt()

def _load_template_with_interview(meta_path: Path) -> dict:
    """Load a template meta file and merge its associated interview components.

    Returns the meta dict with `fields` (from interview `components`) and `rules`
    populated. If the interview file is missing, fields and rules are empty lists.
    """
    meta = json.loads(meta_path.read_text())
    interview_path = TEMPLATES_DATA / meta.get("interviewFile", "")
    if interview_path.exists():
        interview = json.loads(interview_path.read_text())
        meta["fields"] = interview.get("components", [])
        meta["rules"] = interview.get("rules", [])
    else:
        meta["fields"] = []
        meta["rules"] = []
    return meta


def read_templates() -> list:
    out = []
    for f in TEMPLATES_DATA.glob("*_meta.json"):
        try:
            out.append(_load_template_with_interview(f))
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
def ai_status(current_user: dict = Depends(get_current_user)):  
    provider_name = os.environ.get("AI_PROVIDER", "devin")  
    try:  
        get_provider(provider_name, system_prompt=OPENAI_SYSTEM_PROMPT)  
        return {"available": True}  
    except Exception:  
        return {"available": False}

@router.get("/")
def list_templates(current_user: dict = Depends(get_current_user)):
    templates = read_templates()
    if current_user["role"] == "staff":
        templates = [t for t in templates if t.get("active", True)]
    return templates


@router.get("/{template_id}")
def get_template(template_id: str, current_user: dict = Depends(get_current_user)):
    path = TEMPLATES_DATA / f"{template_id}_meta.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    return _load_template_with_interview(path)


@router.post("/")
async def create_template(
    name: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
    interview_json: Optional[str] = Form(None),
    current_user: dict = Depends(require_role("admin"))
):
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")

    template_id = str(uuid.uuid4())
    filename = f"{template_id}.docx"
    upload_path = TEMPLATES_DATA / filename

    content = await file.read()
    upload_path.write_bytes(content)

    if interview_json:
        # Parse and validate user-provided interview definition
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
        # Auto-detect placeholders and create default string questions
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
    (TEMPLATES_DATA / interview_filename).write_text(json.dumps(interview, indent=2))

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

    meta_path = TEMPLATES_DATA / f"{template_id}_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2))
    return _load_template_with_interview(meta_path)


@router.put("/{template_id}")
def update_template(
    template_id: str,
    body: dict,
    current_user: dict = Depends(require_role("admin"))
):
    path = TEMPLATES_DATA / f"{template_id}_meta.json"
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
        interview_path = TEMPLATES_DATA / meta.get("interviewFile", f"{template_id}_interview.json")
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
    return _load_template_with_interview(path)


@router.delete("/{template_id}")
def delete_template(
    template_id: str,
    current_user: dict = Depends(require_role("admin"))
):
    path = TEMPLATES_DATA / f"{template_id}_meta.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    meta = json.loads(path.read_text())
    docx_path = TEMPLATES_DATA / meta.get("documentFile", "")
    interview_path = TEMPLATES_DATA / meta.get("interviewFile", "")
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
        # Detect headings (lines in ALL CAPS or starting with #)
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


def _call_ai(prompt: str, model: str | None = None) -> dict:  
    provider_name = os.environ.get("AI_PROVIDER", "devin")  
    provider = get_provider(provider_name, system_prompt=OPENAI_SYSTEM_PROMPT)  
    kwargs = {}  
    if model:  
        kwargs["model"] = model  
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
    body: GenerateRequest,  
    current_user: dict = Depends(require_role("admin"))  
):  
    TEMPLATES_DATA.mkdir(parents=True, exist_ok=True)  
  
    ai_result = _call_ai(body.prompt)  
    print(ai_result)  
  
    fmt = _get_provider_format()  # reads from schema file

    template_id = str(uuid.uuid4())  
    filename = f"{template_id}.docx"  
    upload_path = TEMPLATES_DATA / filename  
  
    # ── Route 1: URL (Devin) — download files into TEMPLATES_DATA ──  
    if fmt == "url":  
        import httpx as _httpx  
  
        doc_url = ai_result.get("document", "")  
        int_url = ai_result.get("interview", "")  
        if not doc_url or not int_url:  
            raise HTTPException(status_code=500, detail="AI did not return document/interview URLs")  
  
        # Download .docx  
        try:  
            doc_resp = _httpx.get(doc_url, follow_redirects=True, timeout=60)  
            doc_resp.raise_for_status()  
            upload_path.write_bytes(doc_resp.content)  
        except Exception as e:  
            raise HTTPException(status_code=502, detail=f"Failed to download document from {doc_url}: {e}")  
  
        # Download interview JSON  
        try:  
            int_resp = _httpx.get(int_url, follow_redirects=True, timeout=60)  
            int_resp.raise_for_status()  
            interview_data = int_resp.json()  
        except Exception as e:  
            raise HTTPException(status_code=502, detail=f"Failed to download interview from {int_url}: {e}")  
  
        # Extract questions list
        if isinstance(interview_data, dict):
            raw_questions = interview_data.get("components", interview_data.get("questions", []))
        elif isinstance(interview_data, list):
            raw_questions = interview_data
        else:
            raise HTTPException(status_code=500, detail="Unexpected interview format")

    # ── Route 2: base64 (Gemini) — decode into TEMPLATES_DATA ──  
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

    # ── Route 3: legacy (OpenAI) — plain text document_content ──
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
    (TEMPLATES_DATA / interview_filename).write_text(json.dumps(interview, indent=2))

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

    meta_path = TEMPLATES_DATA / f"{template_id}_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2))
    return _load_template_with_interview(meta_path)

@router.post("/{template_id}/regenerate")
def regenerate_template(
    template_id: str,
    body: RegenerateRequest,
    current_user: dict = Depends(require_role("admin"))
):
    path = TEMPLATES_DATA / f"{template_id}_meta.json"
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

    # Overwrite existing docx
    upload_path = TEMPLATES_DATA / meta["documentFile"]
    try:
        _create_docx_from_content(document_content, upload_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create document: {e}")

    interview_filename = meta.get("interviewFile", f"{template_id}_interview.json")
    interview_path = TEMPLATES_DATA / interview_filename
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
    return _load_template_with_interview(path)

# New route to serve generated files safely
@router.get("/download/{filename}")
def download_generated_file(filename: str):
    # allow only simple filenames to prevent path traversal
    if not re.match(r"^[\w\-. ]+\.(json|docx)$", filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "generated"))
    file_path = os.path.abspath(os.path.join(base_dir, filename))
    if not file_path.startswith(base_dir + os.sep):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=filename, media_type="application/octet-stream")
