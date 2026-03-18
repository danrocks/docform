import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Form
from pydantic import BaseModel
from typing import Optional, List
import json, uuid, re, zipfile
from pathlib import Path
from datetime import datetime
from auth_utils import get_current_user, require_role

router = APIRouter()

TEMPLATES_DATA = Path("data/templates")
TEMPLATES_UPLOAD = Path("uploads/templates")


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
    current_user: dict = Depends(require_role("admin"))
):
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")

    template_id = str(uuid.uuid4())
    filename = f"{template_id}.docx"
    upload_path = TEMPLATES_UPLOAD / filename

    content = await file.read()
    upload_path.write_bytes(content)

    placeholders = extract_placeholders_from_docx(upload_path)
    fields = [
        {
            "key": p,
            "label": p.replace("_", " ").title(),
            "type": "text",
            "required": True,
            "placeholder": f"Enter {p.replace('_', ' ').lower()}",
            "options": []
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
