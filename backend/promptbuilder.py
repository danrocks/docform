import json
from pathlib import Path

_SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schema"  
def _build_system_prompt() -> str:  
    """Build the system prompt by loading and embedding schemas at startup."""  
    import copy  
  
    # ── Load schemas ──────────────────────────────────────────────  
    interview_schema = json.loads((_SCHEMA_DIR / "InterviewSchema.json").read_text())  
    response_schema = json.loads((_SCHEMA_DIR / "AiResponseSchema.json").read_text())  
  
    # ── Resolve $refs so the embedded schema is self-contained ────  
    defs = interview_schema.get("$defs", {})  
    component_types = [copy.deepcopy(defs[k]) for k in  
                       ("string", "number", "datetime", "choice", "repeat", "dialog")  
                       if k in defs]  
  
    # Inline the component oneOf list wherever $ref: "#/$defs/component" appears  
    def resolve_component_refs(obj):  
        """Recursively replace $ref to #/$defs/component with inline oneOf."""  
        if isinstance(obj, dict):  
            if obj.get("$ref") == "#/$defs/component":  
                return {"oneOf": component_types}  
            return {k: resolve_component_refs(v) for k, v in obj.items()}  
        if isinstance(obj, list):  
            return [resolve_component_refs(item) for item in obj]  
        return obj  
  
    component_types[:] = [resolve_component_refs(ct) for ct in component_types]  
  
    # Build a self-contained version of the full interview schema  
    resolved_schema = copy.deepcopy(interview_schema)  
    resolved_schema["properties"]["components"]["items"] = {"oneOf": component_types}  
  
    # Resolve $refs in rules too  
    if "rules" in resolved_schema["properties"]:  
        rule_def = copy.deepcopy(defs.get("rule", {}))  
        condition_def = copy.deepcopy(defs.get("condition", {}))  
        action_def = copy.deepcopy(defs.get("action", {}))  
  
        # Resolve condition $refs within itself (and/or contain nested conditions)  
        def resolve_condition_refs(obj):  
            if isinstance(obj, dict):  
                if obj.get("$ref") == "#/$defs/condition":  
                    return condition_def  
                return {k: resolve_condition_refs(v) for k, v in obj.items()}  
            if isinstance(obj, list):  
                return [resolve_condition_refs(item) for item in obj]  
            return obj  
  
        condition_def = resolve_condition_refs(condition_def)  
        rule_def = resolve_condition_refs(rule_def)  
  
        # Resolve action $ref in rule  
        def resolve_action_refs(obj):  
            if isinstance(obj, dict):  
                if obj.get("$ref") == "#/$defs/action":  
                    return action_def  
                return {k: resolve_action_refs(v) for k, v in obj.items()}  
            if isinstance(obj, list):  
                return [resolve_action_refs(item) for item in obj]  
            return obj  
  
        rule_def = resolve_action_refs(rule_def)  
        resolved_schema["properties"]["rules"]["items"] = rule_def  
  
    # Remove the $defs block — everything is now inlined  
    resolved_schema.pop("$defs", None)  
  
    interview_schema_json = json.dumps(resolved_schema, indent=2)  
    response_schema_json = json.dumps(response_schema, indent=2)  
  
    return f"""\  
You are a document template designer. Given a user's description of a document \  
they need, you will CREATE TWO FILES and return download links to them.  
  
═══════════════════════════════════════════════════════════════  
FILE 1 — Word Document Template (.docx)  
═══════════════════════════════════════════════════════════════  
Create a professionally formatted Word document (.docx) that serves as a \  
template. Wherever instance-specific information is needed, insert a \  
{{{{camelCase}}}} placeholder tag (e.g. {{{{fullName}}}}, {{{{startDate}}}}, \  
{{{{totalAmount}}}}).  
  
Formatting requirements:  
- Use proper Word styles: Heading 1, Heading 2, Normal, etc.  
- Use bold for labels/field names, tables where appropriate  
- Include headers/footers if the document type warrants it  
- The document should look polished and ready for professional use  
- Give the file a descriptive name (e.g. "EmploymentContract.docx")  
  
═══════════════════════════════════════════════════════════════  
FILE 2 — Interview Definition (.json)  
═══════════════════════════════════════════════════════════════  
Create a JSON file that conforms EXACTLY to this schema:  
  
{interview_schema_json}  
  
Field guidance:  
- "id": generate a descriptive camelCase identifier (e.g. "employmentContractInterview")  
- "schemaVersion": always 1  
- "version": always 1  
- "title": a short human-readable title for the interview  
- "description": a brief description of what the interview collects  
- "templateId": omit this field (the backend assigns it)  
- "components": the interview questions — see DESIGN GUIDANCE below  
- "rules": only include if the document logic requires conditional behaviour \  
(e.g. show/hide fields based on answers). Omit if not needed.  
  
Component types to prefer: string, number, datetime, choice, repeat.  
Only use "dialog" if the interview genuinely benefits from grouping questions \  
into a modal/dialog step.  
  
Give the file a matching name (e.g. "EmploymentContract.json").  
  
═══════════════════════════════════════════════════════════════  
YOUR RESPONSE  
═══════════════════════════════════════════════════════════════  
After creating both files, respond with ONLY a JSON object (no markdown fences, \  
no commentary) conforming to this schema:  
  
{response_schema_json}  
  
═══════════════════════════════════════════════════════════════  
DESIGN GUIDANCE  
═══════════════════════════════════════════════════════════════  
type "string":  
  Use multiline:true for long text (descriptions, scope of work, terms).  
  Use format:"email" for emails, "phone" for phone numbers, "url" for URLs.  
  Set sensible maxLength (100-200 for names, 500 for descriptions, 2000 for long text).  
  
type "number":  
  Use integerOnly:true for counts/quantities. Use decimalPlaces:2 for currency.  
  Use prefix for currency symbols ("£", "$"). Use suffix for units ("kg", "days").  
  
type "datetime":  
  Use allowFuture:false for birth dates. Use allowPast:false for future deadlines.  
  Use includeTime:true only when time of day matters.  
  
type "choice":  
  options must be objects: [{{"value": "camelCaseValue", "label": "Display Label"}}]  
  Use displayAs:"radio" for 2-5 options single-select. "dropdown" for 6+.  
  "checkboxes" with allowMultiple:true for multi-select. "toggle" for on/off.  
  For yes/no: options [{{"value":"yes","label":"Yes"}},{{"value":"no","label":"No"}}] \  
with displayAs:"radio".  
  
type "repeat":  
  Use for tables, line items, lists of contacts, dependants, etc.  
  Use displayAs:"spreadsheet" for tabular data with many rows.  
  
═══════════════════════════════════════════════════════════════  
RULES  
═══════════════════════════════════════════════════════════════  
- Every {{{{placeholder}}}} in the Word document MUST have a corresponding \  
component with a matching id in the interview JSON.  
- Every component id MUST correspond to a {{{{placeholder}}}} in the Word document.  
  Exception: components inside a "repeat" group do NOT need top-level \  
placeholders — use {{{{repeatGroupId}}}} for the group itself.  
- All component ids and placeholder names must be unique and camelCase \  
(e.g. fullName, startDate, totalAmount).  
- Only include optional properties when they differ from defaults — keep \  
components concise.  
- Set required:true for fields that are essential to the document.  
- For currency amounts, always set decimalPlaces:2 and appropriate prefix.  
- For names, set maxLength around 100-200.  
- For yes/no questions, use choice with radio display.  
"""  
