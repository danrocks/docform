# Backend tests

Automated tests for the DocForm FastAPI backend. Tests run against the
**JSON storage backend** with temp directories (no PostgreSQL required) and are
fully isolated from the repo tree.

## Running the tests

From `backend/` with the virtualenv active:

```bash
python -m pytest tests/ -q            # run everything
python -m pytest tests/test_answersets.py -q   # a single file
python -m pytest tests/test_answersets.py::TestUpdateConcurrency -q   # a single class
python -m pytest -k "concurrency" -q  # filter by name
```

Prerequisites:

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt pytest
```

- **No database needed** — `conftest.py` forces `STORAGE_BACKEND=json` and points
  every repo file at a temp dir.
- **LibreOffice is optional** — document tests render `.docx` regardless; PDF
  conversion is only exercised when LibreOffice is on `PATH` (otherwise the PDF
  path is `None` and the relevant test skips or asserts the "unavailable" case).

## Layout

| File | Type | What it covers |
|------|------|----------------|
| `conftest.py` | fixtures | Temp-dir isolation, seeded roles/tenants, and auth-token fixtures (`admin_token`, `staff_token`, `admin_token_tenant_b`, `superadmin_token`) plus `tenant_headers()` / `admin_headers()` helpers. |
| `test_answersets.py` | API / integration | Answerset lifecycle via `TestClient`: create (+docx render), get, list/pagination/filtering, optimistic-concurrency update (409 on stale version), clone, share, delete, regenerate, download, audit trail, access control & tenant isolation. |
| `test_document_generation.py` | unit | `_generate_documents` (docx render, PDF branches via mocked `shutil.which`/`subprocess.run`) and `_calculate_completion` (progress metric, incl. dialog/repeat handling). |
| `test_expression_eval.py` | unit | Computed-field expression parsing/evaluation. |
| `test_users.py` | API / integration | User CRUD, auth, password rules. |
| `test_roles.py` | API / integration | Role management. |
| `test_tenancy.py` | API / integration | Multi-tenant isolation (cross-subdomain token rejection, etc.). |
| `test_template_visibility.py` | API / integration | Template access restricted by workgroup. |
| `test_workgroups.py` | API / integration | Workgroup CRUD, membership, template links, cascade deletes. |

## Test types

- **API / integration (regression) tests** drive real HTTP requests through
  `fastapi.testclient.TestClient` (routing → auth → route logic → repos →
  filesystem) and assert status codes and response bodies.
- **Unit tests** import and call functions directly, mocking external
  dependencies (e.g. LibreOffice) where needed.

## Writing new tests

- Reuse the token fixtures and `tenant_headers("<slug>", token)` from `conftest.py`.
- For routes that write files under `BACKEND_ROOT` (answersets, submissions,
  templates), follow the `answersets_env` fixture in `test_answersets.py`: patch
  `BACKEND_ROOT` in both `file_utils` and the route module, and redirect any
  extra repo files (e.g. `ANSWERSET_METADATA_FILE`, `AUDIT_LOG_FILE`) to the
  temp dir.
- Seed templates on disk with a real `.docx` built via `python-docx` so
  `docxtpl` rendering is exercised end-to-end (see `seed_template()`).
