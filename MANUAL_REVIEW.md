# Manual review guide — Cross-entity search & bulk document generation

How to manually verify the two features added in this PR. Covers both the API
(via `curl`) and the UI. If anything below doesn't behave as described, the
feature is broken — note it on the PR.

## Prerequisites

1. **Backend** (from `backend/`):
   ```bash
   python -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   uvicorn main:app --reload --port 8000
   ```
   The JSON backend is the default in dev; no database is required. On first
   boot the app seeds two tenants (`demo`, `girlguides`) and users
   `admin`/`admin123`, `staff`/`staff123` per tenant.
2. **Frontend** (from `frontend/`):
   ```bash
   npm install
   npm run dev
   ```
3. Multi-tenancy resolves the tenant from the subdomain, so log in at a tenant
   subdomain, e.g. **http://demo.localhost:3000** (not bare `localhost`).
4. Create some data to search/generate against: log in as `admin`, upload or
   open a template, and create a few submissions/answersets (e.g. with a
   customer name like "Acme").

---

## Feature 1 — Cross-entity search

### UI walkthrough
1. Log in at `http://demo.localhost:3000` and click **Search** in the left nav
   (top, under Dashboard).
2. Type a term that appears in a template name, an answer value, or a
   submitter's name (e.g. `Acme`) and press Enter.
3. **Expect:** three grouped sections — **Templates**, **Submissions**,
   **Answersets** — each showing a count and matching rows. The result count
   ("N results for …") appears above them.
4. Click any result row.
   **Expect:** you navigate to that item's detail/edit page.
5. Search a nonsense term (e.g. `zzzzzz`).
   **Expect:** "0 results" and each section shows its empty message.
6. The query is in the URL (`/search?q=Acme`) — reload the page.
   **Expect:** the same results reload (query is bookmarkable).

### Access / isolation checks
7. Log out, log in as `staff`/`staff123` on the same subdomain, and repeat a
   search that would match another user's submission/answerset.
   **Expect:** staff see only **their own** submissions and answersets (plus
   ones shared with them or in their workgroup); they do **not** see other
   users' items. Templates are limited to ones they're allowed to use.
8. Log in on a **different** tenant (`http://girlguides.localhost:3000`) and
   search for a term you know only exists in `demo`.
   **Expect:** 0 results — no cross-tenant leakage.

### API check
```bash
# Get a token
TOKEN=$(curl -s -X POST http://demo.localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | jq -r .access_token)

# Search
curl -s "http://demo.localhost:8000/api/search/?q=acme" \
  -H "Authorization: Bearer $TOKEN" | jq
```
**Expect:** JSON `{ query, templates[], submissions[], answersets[], total }`.
An empty `q` returns HTTP 422; no token returns HTTP 401.

---

## Feature 2 — Bulk document generation

### UI walkthrough
1. Log in as `admin` and open **Answersets**.
2. **Expect:** a checkbox column on the left, plus a header checkbox that
   selects/clears all rows on the page.
3. Tick two or more rows.
   **Expect:** a **"Regenerate N selected"** button appears at the right of the
   filter bar.
4. Click it.
   **Expect:** a spinner while it runs, then a success toast
   ("Regenerated N documents"), the selection clears, and the list refreshes
   with the affected rows showing status **generated**.
5. Open one of those answersets and download its document.
   **Expect:** a freshly rendered `.docx` (PDF too, if LibreOffice is installed
   on the server — otherwise only `.docx`).

### API check
```bash
curl -s -X POST "http://demo.localhost:8000/api/answersets/bulk-generate" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"ids":["<id1>","<id2>"]}' | jq
```
**Expect:** `{ results:[{id,status,docx_path,pdf_path}], succeeded, failed }`.
Each id is processed independently:
- a valid, accessible id → `status: "generated"`;
- an unknown id (or one in another tenant) → `status: "error", error: "not_found"`;
- an id the caller can't access (e.g. staff on someone else's answerset) →
  `status: "error", error: "forbidden"`.
A single bad id does **not** abort the others in the batch.

---

## Automated tests backing these features

```bash
cd backend && source venv/bin/activate
python -m pytest tests/test_search.py tests/test_bulk_generate.py -q
```
- `tests/test_search.py` — matching, case-insensitivity, empty query (422),
  auth (401), staff vs admin visibility, cross-tenant isolation.
- `tests/test_bulk_generate.py` — multi-generate, per-id error reporting,
  forbidden for non-owner staff, cross-tenant not-found, empty list.
