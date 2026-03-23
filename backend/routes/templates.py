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
from ..config import settings
router = APIRouter()

TEMPLATES_DATA = Path("data/templates")
TEMPLATES_UPLOAD = Path("uploads/templates")

OPENAI_SYSTEM_PROMPT = """You are a document template designer. Given a user's description of a document they need, produce:
1. A professional word document template with {{placeholder_name}} tags (snake_case) wherever instance-specific information is needed.
2. An interview \u2014 a structured list of questions someone would answer to fill in all the placeholders.

Return a JSON object with keys: template (JSON), docx_base64 (base64 of a .docx file), filename (suggested filename). You may include json_filename/docx_filename keys. Backend will save files and publish download paths."

The template JSON must have this exact structure:
{
  "document_content": "FULL DOCUMENT TEXT WITH {{placeholders}}...",
  "questions": [
    {
      "key": "placeholder_name",
      "label": "Human readable question?",
      "type": "string | number | date | multiplechoice",
      "required": true,
      "placeholder": "hint text",
      "help_text": "Guidance for the person answering",
      "config": { ... }
    }
  ]
}

TYPES AND THEIR CONFIG:

type "string" \u2014 for names, addresses, descriptions, any text:
  config: { "min_length": int, "max_length": int|null, "multiline": bool, "pattern": regex|null, "pattern_description": string|null }
  Use multiline:true for long text like descriptions, scope of work, terms.
  Use pattern for emails, phone numbers, postcodes etc.
  Set sensible max_length (e.g. 100 for names, 500 for descriptions, 2000 for long text).

type "number" \u2014 for amounts, quantities, percentages:
  config: { "min": number|null, "max": number|null, "integer_only": bool, "decimal_places": int|null, "step": number|null, "unit": string|null }
  Use integer_only:true for counts, quantities. Use decimal_places:2 for currency. Set unit for display (e.g. "\u00a3", "%", "days").

type "date" \u2014 for dates and deadlines:
  config: { "format": "YYYY-MM-DD", "min_date": string|null, "max_date": string|null, "allow_future": bool, "allow_past": bool, "include_time": bool }
  Use allow_future:false for birth dates. Use allow_past:false for future deadlines.

type "multiplechoice" \u2014 for selections from predefined options:
  config: { "options": ["opt1","opt2",...], "allow_multiple": bool, "min_selections": int, "max_selections": int|null, "display_as": "dropdown"|"radio"|"checkboxes" }
  Use display_as:"radio" for 2-5 options single-select. Use "dropdown" for 6+ options. Use "checkboxes" with allow_multiple:true for multi-select.

RULES:
- Every {{placeholder}} in the document MUST have a corresponding question
- Every question MUST correspond to a {{placeholder}} in the document
- Use snake_case for all placeholder keys
- Choose the most appropriate type for each piece of data
- Set sensible config values \u2014 don't leave everything as defaults
- For currency amounts, always set decimal_places:2 and appropriate unit
- For names, set max_length around 100-200
- For yes/no questions, use multiplechoice with options ["Yes","No"] and display_as:"radio"
"""


def read_templates() -> list:
    out = []
    for f in TEMPLATES_DATA.glob("*.json"):
        try:
            out.append(json.loads(f.read_text()))
        except Exception:
            pass
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
    print ("Debug: checking AI status")
    #comsole_log = f"Calling OpenAI API with model {model} and prompt: {prompt[:100]}..."
    #print(comsole_log)
    
    # logging.basicConfig(level=logging.INFO)   
    # logger = logging.getLogger(__name__)  # at top of module
    # logger.debug("Detailed debug info")
    # logger.info("Calling OpenAI API")
    api_key = os.environ.get("OPENAI_API_KEY", settings.OPENAI_API_KEY)
    sys.stdout.write(f"Key {api_key}\n")
    return {"available": bool(api_key)}


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
    upload_path = TEMPLATES_UPLOAD / filename

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
    docx_path = TEMPLATES_UPLOAD / template["stored_filename"]
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



def _call_openai(prompt, model):
    import json
    import re
    import openai

    api_key = os.environ.get("OPENAI_API_KEY", settings.OPENAI_API_KEY)  
    if not api_key:
        raise HTTPException(status_code=501, detail="AI generation not configured")

    text = None

    # Try new OpenAI client first
    try:
        client = openai.OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
        model=model,
            messages=[
                {"role": "system", "content": OPENAI_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            #temperature=1.5,
            max_tokens=2000,
        )
        print(f"    Debug: raw AI response object {resp}")
        # try several ways to extract the message content
        try:
            text = resp.choices[0].message.content
        except Exception:
            print(f"    Debug: OpenAI API call failed (new client): {e}")
            try:
                text = resp.choices[0].message["content"]
            except Exception:
                try:
                    text = resp.choices[0].text
                except Exception:
                    text = str(resp)
    except Exception as e:
        print(f"    Debug: OpenAI API call failed (new client): {e}")
    print("here")
    # Fallback to older openai package if needed
    if not text:
        try:
            import openai
            openai.api_key = api_key
            resp = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": OPENAI_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=2000,
            )
            try:
                text = resp.choices[0].message.content
            except Exception:
                try:
                    text = resp.choices[0].message["content"]
                except Exception:
                    try:
                        text = resp.choices[0].text
                    except Exception:
                        text = str(resp)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI API error: {e}")

    print(f"    Debug: raw AI response {text[:500]}...")
    # parse JSON from model output robustly
    try:
        parsed = json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            raise ValueError("AI response did not contain valid JSON")
        parsed = json.loads(m.group(0))
    return parsed


@router.post("/generate")
def generate_template(
    body: GenerateRequest,
    current_user: dict = Depends(require_role("admin"))
):
    api_key = os.environ.get("OPENAI_API_KEY", settings.OPENAI_API_KEY)
    if not api_key:
        raise HTTPException(status_code=501, detail="AI generation not configured")

    model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    ai_result = _call_openai(body.prompt, model)

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
    upload_path = TEMPLATES_UPLOAD / filename

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
    upload_path = TEMPLATES_UPLOAD / template["stored_filename"]
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


async def generate_template(body, request: Request):
    # ...existing code...
    try:
        ai_result = _call_openai(body.prompt, body.model if getattr(body, "model", None) else "gpt-4o")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI call failed: {e}")

    print(f"Debug: AI result {ai_result}")
    

    # output directory (ensure inside project backend/generated)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "generated"))
    os.makedirs(base_dir, exist_ok=True)

    # create base filename
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    base_name = f"{timestamp}_{uuid.uuid4().hex}"

    # save JSON template
    template_obj = ai_result.get("template") or ai_result.get("json_template") or ai_result
    json_filename = ai_result.get("json_filename") or f"{base_name}.json"
    # sanitize
    json_filename = re.sub(r"[\\/]+", "_", json_filename)
    if not json_filename.lower().endswith(".json"):
        json_filename = f"{json_filename}.json"
    json_path = os.path.join(base_dir, json_filename)
    try:
        with open(json_path, "w", encoding="utf-8") as jf:
            if isinstance(template_obj, str):
                try:
                    parsed = json.loads(template_obj)
                    json.dump(parsed, jf, ensure_ascii=False, indent=2)
                except Exception:
                    jf.write(template_obj)
            else:
                json.dump(template_obj, jf, ensure_ascii=False, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed saving JSON template: {e}")

    # save docx if present
    docx_b64 = ai_result.get("docx_base64") or ai_result.get("docx")
    docx_filename: Optional[str] = None
    if docx_b64:
        try:
            docx_bytes = base64.b64decode(docx_b64)
            suggested = ai_result.get("filename") or ai_result.get("docx_filename") or f"{base_name}.docx"
            # sanitize suggested filename
            suggested = re.sub(r"[\\/]+", "_", suggested)
            suggested = re.sub(r"[^\w\-. ]+", "", suggested)
            if not suggested.lower().endswith(".docx"):
                suggested = f"{suggested}.docx"
            docx_filename = suggested
            docx_path = os.path.join(base_dir, docx_filename)
            with open(docx_path, "wb") as df:
                df.write(docx_bytes)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed decoding/saving docx: {e}")

    # build download paths (these are the paths returned to the caller / "ai should return paths")
    # assume this router is mounted at /templates in main app
    ai_result["json_path"] = f"/templates/download/{json_filename}"
    ai_result["docx_path"] = f"/templates/download/{docx_filename}" if docx_filename else None

    # remove large base64 before returning
    ai_result.pop("docx_base64", None)
    ai_result.pop("docx", None)

    # return the AI result (now contains json_path/docx_path) so client can download individually
    return ai_result

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
