from typing import Any, Dict, Optional
import os
import json
import re

from fastapi import HTTPException
from ai_providers import AIProvider, register_provider


@register_provider("openai")
class OpenAIProvider(AIProvider):
    """
    Wrapper around the OpenAI call logic. Single class, single call() method.
    """

    def __init__(self, model: str = "gpt-4o", api_key: Optional[str] = None, system_prompt: Optional[str] = None):
        self.model = model
        self.api_key = api_key
        self.system_prompt = system_prompt

    def call(self, prompt: str, *, mode: str = "document", model: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        model = model or self.model

        api_key = self.api_key or os.environ.get("OPENAI_API_KEY")
        system_prompt = self.system_prompt
        if not api_key:
            # try project settings if present
            try:
                from ..config import settings as _settings  # adjust to your project layout if needed
                api_key = getattr(_settings, "OPENAI_API_KEY", None)
                if system_prompt is None:
                    system_prompt = getattr(_settings, "OPENAI_SYSTEM_PROMPT", None)
            except Exception:
                pass

        if not api_key:
            raise HTTPException(status_code=501, detail="AI generation not configured")

        text = None

        # Try new OpenAI client first
        try:
            import openai as _openai_new  # the new openai package exposes OpenAI(...)
            client = _openai_new.OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=4000,
            )
            try:
                if getattr(resp.choices[0], "finish_reason", None) == "length":
                    raise ValueError("OpenAI response truncated due to max_tokens limit")
            except Exception:
                pass

            # robust extraction of textual content
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
        except Exception:
            text = None

        # Fallback to older openai package if needed
        if not text:
            try:
                import openai as _openai_old
                _openai_old.api_key = api_key
                resp = _openai_old.ChatCompletion.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
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

        # parse JSON from model output robustly
        try:
            parsed = json.loads(text)
        except Exception:
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if not m:
                raise ValueError("AI response did not contain valid JSON")
            parsed = json.loads(m.group(0))

        return parsed