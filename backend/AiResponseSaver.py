import json
import base64
import uuid
from pathlib import Path
from typing import Optional, Tuple, Union

from docx import Document
import jsonschema


class AiResponseSaver:
    """
    Parse a JSON string (which must adhere to a JSON Schema file like
    "schema/AiResponseSchema.json"), extract 'document' and 'interview'
    fields and save them under a backend-relative output folder (default:
    data/templates).

    - document -> .docx (accepts plain text, base64 text, or base64 binary .docx)
    - interview -> .json (accepts JSON object/array, JSON string, or base64-encoded JSON)

    Methods:
      save_from_json_string(json_string, schema_path, output_rel=None, stem=None)
    """

    def __init__(self, backend_root: Optional[Union[str, Path]] = None, default_output_rel: str = "data/templates"):
        self.backend_root = Path(backend_root or Path.cwd()).resolve()
        self.default_output_rel = default_output_rel

    def save_from_json_string(
        self,
        json_string: str,
        schema_path: str,
        output_rel: Optional[str] = None,
        stem: Optional[str] = None,
    ) -> Tuple[Path, Path]:
        """
        Validate json_string against schema_path (resolved relative to backend_root if needed),
        then save document and interview fields to disk. Returns (docx_path, interview_json_path).
        """
        schema_file = Path(schema_path)
        if not schema_file.is_absolute():
            schema_file = (self.backend_root / schema_file).resolve()
        if not schema_file.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_file}")

        schema = json.loads(schema_file.read_text(encoding="utf-8"))

        try:
            data = json.loads(json_string)
        except json.JSONDecodeError as e:
            raise ValueError(f"Provided string is not valid JSON: {e}") from e

        # validate against schema
        try:
            jsonschema.validate(instance=data, schema=schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"JSON does not conform to schema: {e.message}") from e

        # find fields (case-insensitive fallback)
        document_content = self._find_key(data, "document")
        interview_content = self._find_key(data, "interview")

        if document_content is None:
            raise ValueError("Schema-valid JSON missing required 'document' field.")
        if interview_content is None:
            raise ValueError("Schema-valid JSON missing required 'interview' field.")

        out_rel = output_rel or self.default_output_rel
        out_dir = (self.backend_root / out_rel).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        file_stem = stem or "schema"
        docx_path = self._save_document_as_docx(document_content, file_stem, out_dir)
        interview_path = self._save_interview_as_json(interview_content, file_stem, out_dir)
        return docx_path, interview_path

    def _find_key(self, data: dict, key_name: str):
        if key_name in data:
            return data[key_name]
        for k, v in data.items():
            if k.lower() == key_name.lower():
                return v
        return None

    def _save_document_as_docx(self, content: Union[str, bytes, dict], stem: str, out_dir: Path) -> Path:
        if content is None:
            raise ValueError("Document content is empty")

        # If bytes: write directly as .docx bytes
        if isinstance(content, (bytes, bytearray)):
            path = out_dir / self._unique_name(stem, ".docx")
            path.write_bytes(bytes(content))
            return path

        # Try base64 decode -> if looks like .docx (zip header "PK") write bytes; if decodes to text use it
        text_candidate: Optional[str] = None
        try:
            decoded = base64.b64decode(content, validate=True)
            if self._looks_like_docx_bytes(decoded):
                path = out_dir / self._unique_name(stem, ".docx")
                path.write_bytes(decoded)
                return path
            try:
                text_candidate = decoded.decode("utf-8")
            except UnicodeDecodeError:
                text_candidate = None
        except Exception:
            text_candidate = None

        text = text_candidate if text_candidate is not None else str(content)

        # create .docx from text (preserve line breaks as paragraphs)
        doc = Document()
        lines = text.splitlines() or [""]
        for line in lines:
            doc.add_paragraph(line)
        path = out_dir / self._unique_name(stem, ".docx")
        doc.save(path)
        return path

    def _save_interview_as_json(self, content: Union[str, bytes, dict, list], stem: str, out_dir: Path) -> Path:
        if content is None:
            raise ValueError("Interview content is empty")

        parsed = None

        if isinstance(content, (bytes, bytearray)):
            # try decode bytes -> JSON
            try:
                txt = bytes(content).decode("utf-8")
                parsed = json.loads(txt)
            except Exception:
                parsed = {"data": bytes(content).hex()}
        else:
            # try base64 decode -> parse JSON
            try:
                decoded = base64.b64decode(content, validate=True)
                try:
                    txt = decoded.decode("utf-8")
                    parsed = json.loads(txt)
                except Exception:
                    parsed = None
            except Exception:
                parsed = None

            if parsed is None:
                if isinstance(content, (dict, list)):
                    parsed = content
                else:
                    try:
                        parsed = json.loads(str(content))
                    except Exception:
                        parsed = {"data": content}

        path = out_dir / self._unique_name(stem, ".json")
        path.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def _looks_like_docx_bytes(self, b: bytes) -> bool:
        return len(b) > 2 and b[:2] == b"PK"

    def _unique_name(self, stem: str, suffix: str) -> str:
        safe = "".join(c for c in (stem or "file") if c.isalnum() or c in ("-", "_")).rstrip("._-")
        if not safe:
            safe = "file"
        return f"{safe}_{uuid.uuid4().hex[:8]}{suffix}"


# Example usage (commented):
# saver = TemplateSaver(backend_root=r"c:\Users\danie\Documents\docform")
# json_str = '{"document":"Hello world","interview":{"q":"a"}}'
# docx_path, interview_path = saver.save_from_json_string(json_str, "schema/AiResponseSchema.json", output_rel="data/templates", stem="AiResponseSchema")
# print(docx_path, interview_path)