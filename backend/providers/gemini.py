from typing import Any, Dict, Optional
from pathlib import Path
from datetime import datetime
import os
import uuid
import json
import re

from fastapi import HTTPException
from ai_providers import AIProvider, register_provider

@register_provider("gemini")
class GeminiProvider(AIProvider):
    """
    Wrapper version of your _call_gemini function.
    - Accepts api_key, model, backend_root, and system_prompt via __init__.
    - call(prompt, mode=...) mirrors the minimal provider contract.
    """

    def __init__(
        self,
        model: str = "gemini",
        api_key: Optional[str] = None,
        backend_root: Optional[Path] = None,
        system_prompt: Optional[str] = None,
    ):
        self.model = model
        self.api_key = api_key
        self.backend_root = Path(backend_root) if backend_root else Path(__file__).resolve().parent.parent
        self.system_prompt = system_prompt

    def call(self, prompt: str, *, mode: str = "document", model: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        mode is accepted for compatibility; this implementation always tries to parse JSON
        from Gemini response and returns the parsed dict.
        Returns the parsed JSON (dict) on success or raises on error.
        """
        model = model or self.model

        # prefer explicit api_key, then env, then optional project settings
        api_key = self.api_key or os.environ.get("GEMINI_KEY")
        if not api_key:
            # attempt to read project settings if available
            try:
                from ..config import settings as _settings  # adjust import if your project uses a different module
                api_key = getattr(_settings, "GEMINI_KEY", None)
                if not self.system_prompt:
                    system_prompt = getattr(_settings, "OPENAI_SYSTEM_PROMPT", None)
                else:
                    system_prompt = self.system_prompt
            except Exception:
                system_prompt = self.system_prompt
        else:
            system_prompt = self.system_prompt

        if not api_key:
            raise HTTPException(status_code=501, detail="AI generation not configured")

        # local import to avoid top-level dependency unless provider is used
        from google import genai

        client = genai.Client(api_key=api_key)

        print(datetime.utcnow().strftime("%Y%m%d %M:%S"))
        print("attempting to call gemini api with model ", model)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={
                "system_instruction": system_prompt,
                "response_mime_type": "application/json",
            },
        )
        print("response complete")
        print(datetime.utcnow().strftime("%Y%m%d %M:%S"))

        if response.candidates and response.candidates[0].finish_reason.name != "STOP":
            raise ValueError(f"Gemini response finish reason: {response.candidates[0].finish_reason.name}")

        text = response.text

        shared_uuid = uuid.uuid4().hex[:8]
        shared_filename = f"AiResponseSchema_{shared_uuid}_shared.json"

        # try to write debug/templ data if TEMPLATES_DATA is available in project
        try:
            from ..paths import TEMPLATES_DATA  # adjust if your project stores this elsewhere
            TEMPLATES_DATA.mkdir(parents=True, exist_ok=True)
            (TEMPLATES_DATA / shared_filename).write_text(text, encoding="utf-8")
        except Exception:
            # not critical; continue without writing
            pass

        try:
            parsed = json.loads(text)
            # try to save using project saver if available
            try:
                from ..saver import AiResponseSaver  # adjust import to your actual saver module
                saver = AiResponseSaver(backend_root=self.backend_root)
                saver.save_from_json_string(
                    text,
                    "schema/AiResponseSchema.json",
                    output_rel="data/templates",
                    stem="AiResponseSchema",
                    file_id=shared_uuid,
                )
            except Exception:
                # saver is optional for provider operation
                pass

            return parsed
        except Exception:
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if not m:
                raise ValueError("AI response did not contain valid JSON")
            return json.loads(m.group(0))