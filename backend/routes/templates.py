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
from question_schema import validate_questions, DEFAULT_CONFIGS
from config import settings
from AiResponseSaver import AiResponseSaver
from datetime import datetime

from prompts.promptbuilder import _build_system_prompt
import providers  # noqa: F401 — triggers provider self-registration  
from ai_providers import get_provider

router = APIRouter()

TEMPLATES_DATA = Path("..") / "data" / "templates"
TEMPLATES_UPLOAD = Path("uploads/templates")

OPENAI_SYSTEM_PROMPT = _build_system_prompt()

def read_templates() -> list:
    out = []
    print("here")
    print(TEMPLATES_DATA)
    for f in TEMPLATES_DATA.glob("*.json"):
        try:
            print(f"Debug: loading template... {f.name}")
            out.append(json.loads(f.read_text()))
        except Exception:
            pass
    print( out)
    return sorted(out, key=lambda x: x.get("created_at", ""), reverse=True)


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
    path = TEMPLATES_DATA / f"{template_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    return json.loads(path.read_text())


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
            raw_questions = json.loads(interview_json)
        except json.JSONDecodeError as e:
            upload_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=f"Invalid interview JSON: {e}")
        try:
            fields = validate_questions(raw_questions)
        except ValueError as e:
            upload_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=str(e))
    else:
        # Auto-detect placeholders and create default string questions
        placeholders = extract_placeholders_from_docx(upload_path)
        fields = [
            {
                "key": p,
                "label": p.replace("_", " ").title(),
                "type": "string",
                "required": True,
                "placeholder": f"Enter {p.replace('_', ' ').lower()}",
                "help_text": "",
                "config": {
                    "min_length": 0,
                    "max_length": None,
                    "multiline": False,
                    "pattern": None,
                    "pattern_description": None
                }
            }
            for p in placeholders
        ]

    template = {
        "id": template_id,
        "name": name,
        "description": description,
        "original_filename": file.filename,
        "stored_filename": filename,
        "fields": fields,
        "active": True,
        "created_at": datetime.utcnow().isoformat(),
        "created_by": current_user["id"],
        "submission_count": 0,
        "generation_method": "upload",
    }

    (TEMPLATES_DATA / f"{template_id}.json").write_text(json.dumps(template, indent=2))
    return template


@router.put("/{template_id}")
def update_template(
    template_id: str,
    body: dict,
    current_user: dict = Depends(require_role("admin"))
):
    path = TEMPLATES_DATA / f"{template_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    template = json.loads(path.read_text())
    allowed = {"name", "description", "fields", "active"}
    for k, v in body.items():
        if k in allowed:
            if k == "fields":
                # Validate fields before saving
                try:
                    v = validate_questions(v)
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=str(e))
            template[k] = v
    template["updated_at"] = datetime.utcnow().isoformat()
    path.write_text(json.dumps(template, indent=2))
    return template


@router.delete("/{template_id}")
def delete_template(
    template_id: str,
    current_user: dict = Depends(require_role("admin"))
):
    path = TEMPLATES_DATA / f"{template_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    template = json.loads(path.read_text())
    docx_path = TEMPLATES_DATA / template["stored_filename"]
    if docx_path.exists():
        docx_path.unlink()
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

@router.post("/generate")
def generate_template(
    body: GenerateRequest,
    current_user: dict = Depends(require_role("admin"))
):
    api_key = os.environ.get("OPENAI_API_KEY", settings.OPENAI_API_KEY)
    if not api_key:
        raise HTTPException(status_code=501, detail="AI generation not configured")

    model = os.environ.get("OPENAI_MODEL", "gpt-4o")
    print(body.prompt)
    
    ai_result = _call_ai(body.prompt)
    print(ai_result)

    document_content = ai_result.get("document_content", "")
    raw_questions = ai_result.get("questions", [])

    if not document_content:
        raise HTTPException(status_code=500, detail="AI did not generate document content")
    if not raw_questions:
        raise HTTPException(status_code=500, detail="AI did not generate interview questions")

    # Validate questions
    try:
        fields = validate_questions(raw_questions)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"AI generated invalid questions: {e}")

    # Create docx file
    template_id = str(uuid.uuid4())
    filename = f"{template_id}.docx"
    # upload_path = TEMPLATES_UPLOAD / filename
    upload_path = TEMPLATES_DATA / filename

    try:
        _create_docx_from_content(document_content, upload_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create document: {e}")

    template = {
        "id": template_id,
        "name": body.name,
        "description": body.description or "",
        "original_filename": f"{body.name.replace(' ', '_')}.docx",
        "stored_filename": filename,
        "fields": fields,
        "active": True,
        "created_at": datetime.utcnow().isoformat(),
        "created_by": current_user["id"],
        "submission_count": 0,
        "generation_method": "ai",
        "original_prompt": body.prompt,
    }

    (TEMPLATES_DATA / f"{template_id}.json").write_text(json.dumps(template, indent=2))
    return template


@router.post("/{template_id}/regenerate")
def regenerate_template(
    template_id: str,
    body: RegenerateRequest,
    current_user: dict = Depends(require_role("admin"))
):
    path = TEMPLATES_DATA / f"{template_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Template not found")

    api_key = os.environ.get("OPENAI_API_KEY", settings.OPENAI_API_KEY )
    if not api_key:
        raise HTTPException(status_code=501, detail="AI generation not configured")

    model = os.environ.get("OPENAI_MODEL", "gpt-4o")
    template = json.loads(path.read_text())

    ai_result = _call_openai(body.prompt, model)

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
    upload_path = TEMPLATES_DATA / template["stored_filename"]
    try:
        _create_docx_from_content(document_content, upload_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create document: {e}")

    template["fields"] = fields
    template["original_prompt"] = body.prompt
    template["generation_method"] = "ai"
    template["updated_at"] = datetime.utcnow().isoformat()

    path.write_text(json.dumps(template, indent=2))
    return template

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
