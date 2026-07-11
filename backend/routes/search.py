"""Cross-entity search.

Provides a single tenant-scoped endpoint that searches across templates,
submissions, and answersets in one request. Results honour the same
access rules the individual list endpoints use:

  * admins and approvers see everything in their tenant;
  * staff see only templates they may use, and only their own (or
    shared / workgroup) submissions and answersets.

Matching is a simple case-insensitive substring search over the
human-meaningful text fields of each entity (names, context, and — for
submissions/answersets — the string values of the answers).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from file_utils import TEMPLATE_META_FILENAME, get_tenant_data_dir
from repositories.factory import (
    get_answerset_metadata_repository,
    get_workgroup_user_repository,
)
from routes.submissions import _user_has_template_access
from tenant_context import verify_tenant_match

router = APIRouter()

# Cap results per entity type so a broad query can't return an unbounded payload.
PER_TYPE_LIMIT = 25


def _match(query: str, *values) -> bool:
    """Return True if *query* is a substring of any of *values* (case-insensitive)."""
    for v in values:
        if v is None:
            continue
        if query in str(v).lower():
            return True
    return False


def _data_text(data: dict) -> str:
    """Flatten the string-ish leaf values of a submission/answerset ``data`` dict."""
    if not isinstance(data, dict):
        return ""
    parts: list[str] = []

    def walk(value):
        if isinstance(value, dict):
            for v in value.values():
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)
        elif isinstance(value, (str, int, float)):
            parts.append(str(value))

    walk(data)
    return " ".join(parts)


def _user_workgroup_ids(user_id: str) -> list[str]:
    links = get_workgroup_user_repository().get_user_workgroups(user_id)
    return [r["workgroup_id"] for r in links]


def _iter_submission_files(base: Path):
    """Yield every submission JSON file for a tenant, including workgroup subdirs."""
    if not base.exists():
        return
    for f in base.glob("*.json"):
        yield f
    wg_root = base / "workgroups"
    if wg_root.exists():
        for wg_dir in wg_root.iterdir():
            if wg_dir.is_dir():
                yield from wg_dir.glob("*.json")


def _search_templates(request: Request, q: str, current_user: dict) -> list[dict]:
    templates_dir = get_tenant_data_dir(request, "data", "templates")
    tenant_id = current_user.get("tenant_id")
    results: list[dict] = []
    if not templates_dir.exists():
        return results
    for child in sorted(templates_dir.iterdir()):
        if not child.is_dir():
            continue
        meta_path = child / TEMPLATE_META_FILENAME
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:
            continue
        template_id = meta.get("id", child.name)
        if not _match(q, meta.get("name"), meta.get("description"), template_id):
            continue
        if not _user_has_template_access(template_id, current_user, tenant_id):
            continue
        results.append({
            "id": template_id,
            "name": meta.get("name", ""),
            "description": meta.get("description", ""),
            "active": meta.get("active", False),
        })
        if len(results) >= PER_TYPE_LIMIT:
            break
    return results


def _search_submissions(request: Request, q: str, current_user: dict) -> list[dict]:
    base = get_tenant_data_dir(request, "data", "submissions")
    is_staff = current_user["role"] == "staff"
    results: list[dict] = []
    for f in _iter_submission_files(base):
        try:
            sub = json.loads(f.read_text())
        except Exception:
            continue
        if is_staff and sub.get("submitted_by") != current_user["id"]:
            continue
        if not _match(
            q,
            sub.get("template_name"),
            sub.get("context"),
            sub.get("submitted_by_name"),
            _data_text(sub.get("data", {})),
        ):
            continue
        results.append({
            "id": sub.get("id"),
            "template_name": sub.get("template_name", ""),
            "status": sub.get("status", ""),
            "submitted_by_name": sub.get("submitted_by_name", ""),
            "submitted_at": sub.get("submitted_at", ""),
        })
    results.sort(key=lambda x: x.get("submitted_at", ""), reverse=True)
    return results[:PER_TYPE_LIMIT]


def _search_answersets(request: Request, q: str, current_user: dict) -> list[dict]:
    meta_repo = get_answerset_metadata_repository()
    tenant_id = current_user.get("tenant_id")
    items = meta_repo.get_all(tenant_id=tenant_id)

    is_staff = current_user["role"] == "staff"
    workgroup_ids = set(_user_workgroup_ids(current_user["id"])) if is_staff else set()

    results: list[dict] = []
    for m in items:
        if is_staff:
            is_owner = m.get("submitted_by") == current_user["id"]
            is_shared = current_user["id"] in (m.get("shared_with") or [])
            is_member = bool(m.get("workgroup_id")) and m.get("workgroup_id") in workgroup_ids
            if not (is_owner or is_shared or is_member):
                continue
        if not _match(q, m.get("template_name"), m.get("context"), m.get("submitted_by_name")):
            continue
        results.append({
            "id": m.get("id"),
            "template_name": m.get("template_name", ""),
            "status": m.get("status", ""),
            "submitted_by_name": m.get("submitted_by_name", ""),
            "submitted_at": m.get("submitted_at", ""),
            "workgroup_id": m.get("workgroup_id"),
        })
        if len(results) >= PER_TYPE_LIMIT:
            break
    return results


@router.get("/")
def search(
    request: Request,
    q: str = Query(..., min_length=1, description="Search query"),
    current_user: dict = Depends(verify_tenant_match),
):
    q_norm = q.strip().lower()
    templates = _search_templates(request, q_norm, current_user)
    submissions = _search_submissions(request, q_norm, current_user)
    answersets = _search_answersets(request, q_norm, current_user)
    return {
        "query": q,
        "templates": templates,
        "submissions": submissions,
        "answersets": answersets,
        "total": len(templates) + len(submissions) + len(answersets),
    }
