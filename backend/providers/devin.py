from typing import Any, Dict, Optional  
from pathlib import Path  
import os  
import uuid  
import json  
import asyncio  
  
import httpx  
from fastapi import HTTPException  
from ai_providers import AIProvider, register_provider  

@register_provider("devin")  
class DevinProvider(AIProvider):  
    """  
    Devin session-based provider. Creates a Devin session that uses python-docx  
    to build properly formatted Word documents, then returns results via  
    structured_output. Natively async due to session polling.  
    """  
  
    DEVIN_API_BASE = "https://api.devin.ai/v1"  
    MAX_POLL_SECONDS = 600  
    POLL_INTERVAL = 10  
  
    def __init__(  
        self,  
        model: str = "devin",  
        api_key: Optional[str] = None,  
        backend_root: Optional[Path] = None,  
        system_prompt: Optional[str] = None,  
    ):  
        self.model = model  
        self.api_key = api_key  
        self.backend_root = Path(backend_root) if backend_root else Path(__file__).resolve().parent.parent  
        self.system_prompt = system_prompt  
  
    def _get_api_key(self) -> str:  
        api_key = self.api_key or os.environ.get("DEVIN_KEY")  
        if not api_key:  
            try:  
                from config import settings as _settings  
                api_key = getattr(_settings, "DEVIN_KEY", None)  
            except Exception:
                pass  
        if not api_key:  
            raise HTTPException(status_code=501, detail="Devin key not configured")  
        return api_key  
  
    def _get_system_prompt(self) -> str:  
        system_prompt = self.system_prompt  
        if not system_prompt:  
            try:  
                from config import settings as _settings  
                system_prompt = getattr(_settings, "OPENAI_SYSTEM_PROMPT", None)  
            except Exception:  
                pass  
        return system_prompt or ""  
  
    def _build_session_prompt(self, prompt: str, system_prompt: str) -> str:  
        return f"""\  
You are working on a document template generation system called Docform.  
  
Your task: create TWO files based on the user's request below, then output  
them as a JSON object via structured_output.  
  
INSTRUCTIONS:  
Get system instructions from web page https://github.com/danrocks/docform/blob/master/backend/prompts/devinprompt.md.
The web page includes detailed instructions and examples for how to format the document and interview JSON, including how to represent placeholders. Follow those instructions carefully.
Follow any links in the instructions to get schema details. 
  
USER REQUEST:  
{prompt}  

CRITICAL — FINAL STEP:  
After creating both files, you MUST use the structured_output tool to return a JSON object with these fields:  
- "document": the download URL for the .docx file you created  
- "interview": the download URL for the .json file you created  
- "summary": a brief description of what was created  
- "placeholderCount": the number of unique placeholders  
  
Do NOT consider the task complete until you have called structured_output with this JSON.  

"""  
  
    def _structured_schema(self) -> dict:  
        return {  
            "type": "object",  
            "required": ["document", "interview"],  
            "properties": {  
                "document": {"type": "string", "description": "url to generated Word document"},  
                "interview": {"type": "string", "description": "url to constructed template interview JSON"},  
                "summary": {"type": "string", "description": "Brief description of what was created"},  
                "placeholderCount": {"type": "integer", "minimum": 1, "description": "Number of unique placeholders"},  
            },  
        }  
  
    def _save_output(self, structured_output: dict) -> dict:  
        """Persist raw Devin response JSON to TEMPLATES_DATA for audit."""  
        shared_uuid = uuid.uuid4().hex[:8]  
        json_str = json.dumps(structured_output, indent=2)  
    
        try:  
            TEMPLATES_DATA   = TEMPLATES_DATA = Path(__file__).resolve().parent.parent.parent / "data" / "templates"
            TEMPLATES_DATA.mkdir(parents=True, exist_ok=True)  
            raw_filename = f"DevinResponse_{shared_uuid}.json"  
            (TEMPLATES_DATA / raw_filename).write_text(json_str, encoding="utf-8")  
            print(f"Devin raw response saved: {raw_filename}")  
        except Exception as e:  
            print(f"Warning: failed to save Devin raw response: {e}")  
    
        return structured_output
  
    def call(self, prompt: str, *, mode: str = "document", **kwargs) -> Dict[str, Any]:  
        """Sync fallback — runs the async implementation in an event loop."""  
        try:  
            loop = asyncio.get_running_loop()  
        except RuntimeError:  
            loop = None  
  
        if loop and loop.is_running():  
            # We're inside an async context; can't use asyncio.run().  
            # Caller should use acall() instead.  
            import concurrent.futures  
            with concurrent.futures.ThreadPoolExecutor() as pool:  
                return pool.submit(asyncio.run, self.acall(prompt, mode=mode, **kwargs)).result()  
        else:  
            return asyncio.run(self.acall(prompt, mode=mode, **kwargs))  
  
    async def acall(self, prompt: str, *, mode: str = "document", **kwargs) -> Dict[str, Any]:  
        """Native async implementation — polls Devin session without blocking the event loop."""  
        api_key = self._get_api_key()  
        system_prompt = self._get_system_prompt()  
        session_prompt = self._build_session_prompt(prompt, system_prompt)  
  
        headers = {  
            "Authorization": f"Bearer {api_key}",  
            "Content-Type": "application/json",  
        }  
  
        print(repr(prompt))

        print(repr(session_prompt))

        # 1. Create the session  
        async with httpx.AsyncClient(timeout=30) as client:  
            create_resp = await client.post(  
                f"{self.DEVIN_API_BASE}/sessions",  
                headers=headers,  
                json={  
                    "prompt": session_prompt,  
                    "structured_output": {"schema": self._structured_schema()},  
                },  
            )  
  
        if create_resp.status_code != 200:  
            print(f"Devin session creation error: {create_resp.status_code} {create_resp.text}")
            raise HTTPException(  
                status_code=502,  
                detail=f"Devin session creation failed: {create_resp.status_code} {create_resp.text}",  
            )  
  
        session_id = create_resp.json()["session_id"]  
        print(f"Devin session created: {session_id}")  
  
        # 2. Poll until finished (non-blocking)  
        elapsed = 0  
        status_data = None  
  
        async with httpx.AsyncClient(timeout=30) as client:  
            while elapsed < self.MAX_POLL_SECONDS:  
                await asyncio.sleep(self.POLL_INTERVAL)  
                elapsed += self.POLL_INTERVAL  
  
                status_resp = await client.get(  
                    f"{self.DEVIN_API_BASE}/session/{session_id}",  
                    headers=headers,  
                )  
                if status_resp.status_code != 200:  
                    print(f"Devin poll error: {status_resp.status_code}")  
                    continue  
  
                status_data = status_resp.json()  
                status = status_data.get("status_enum")  
                print(f"Devin session {session_id}: {status} ({elapsed}s)")  
  
                if status == "finished":  
                    print("Devin call finished successfully")
                    break  
                elif status in ("stopped", "failed", "blocked"):  
                    raise HTTPException(  
                        status_code=502,  
                        detail=f"Devin session {status}: {status_data.get('error', 'unknown')}",  
                    )  
            else:  
                raise HTTPException(  
                    status_code=504,  
                    detail=f"Devin session timed out after {self.MAX_POLL_SECONDS}s",  
                )  
  
        # 3. Extract structured output  
        structured_output = status_data.get("structured_output")  
        if not structured_output:  
            raise HTTPException(  
                status_code=502,  
                detail="Devin session finished but returned no structured output",  
            )  
  
        if isinstance(structured_output, str):  
            structured_output = json.loads(structured_output)  
  
        # 4. Save artifacts  
        return self._save_output(structured_output)
    