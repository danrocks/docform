# Docform — Devin Context  
  
> **Last verified**: 2026-05-01  
>  
> **Maintenance rule**: When any Devin session makes a structural or architectural change to this project (new storage backend, new modules, changed workflows, new concepts), update this file as part of that same task. Keep descriptions high-level — focus on *what* and *where*, not implementation detail.  
  
## What is Docform?  
  
Docform is a system for the creation, use, and management of **document templates**. It is built with FastAPI (Python) and React (JavaScript).  
  
## Core Concepts  
  
- **Document Template**: A Word (.docx) document containing `{{placeholder}}` tags that mark where answers will be inserted. Templates are uploaded or AI-generated.  
  
- **Interview**: A set of questions, defined in a standardised JSON format (`InterviewSchema.json`), associated with a document template. Interviews are presented to users as HTML forms in the React frontend. Each question corresponds to one or more placeholders in the template.  
  
- **Answerset**: The result of completing (or partially completing) an interview. Answersets capture the user's responses. They are used to populate a completed instance of the associated document template, and are stored for subsequent re-use or deletion.  
  
- **Completed Instance**: A rendered `.docx` (and optionally `.pdf`) document produced by merging an answerset with its document template.  
  
- **Tenant**: An isolated organisation (business, club, group) identified by a subdomain slug. Each tenant has its own users, templates, interviews, and answersets. Tenants are completely isolated from each other. Data isolation is enforced via `tenant_id` columns (users) and filesystem namespacing (templates, submissions stored in `data/{type}/{tenant_id}/`).  
  
## Architecture  
  
- **Backend**: FastAPI app in `backend/main.py` with routers under `backend/routes/`:  
  - `auth.py` — JWT-based authentication (admin, staff, approver, superadmin roles)  
  - `templates.py` — Template CRUD, upload, field configuration, AI generation  
  - `submissions.py` — Submission creation, document rendering, approval workflow  
  - `users.py` — User CRUD (admin only within tenant, superadmin across tenants)  
  - `tenants.py` — Tenant CRUD (superadmin only, admin subdomain)  
- **Frontend**: React SPA (Vite + Tailwind CSS) in `frontend/`  
- **Storage**: PostgreSQL for user/tenant data (switchable to JSON via `STORAGE_BACKEND=json`). Templates and submissions remain as flat-file JSON in `data/{type}/{tenant_id}/` and binary files in `uploads/`.  
- **AI Generation**: OpenAI and Google Gemini integration for generating templates and interviews from natural language prompts  
- **Multi-tenancy**: Shared database with `tenant_id` column. Tenants are resolved via subdomain from the `Host` header (`tenant_context.py`). The `admin` subdomain is the superadmin context (`tenant_id=None`). The bare domain (`localhost` / `docform.com`) is reserved for a future marketing/sign-up page. JWT tokens contain `tenant_id` and are validated against the subdomain on every request.  
- **Superadmin**: Operates on the `admin` subdomain only. Has `tenant_id=None`. Manages tenants and can manage users across all tenants.  
  
## Key Workflows  
  
1. **Template Creation**: Admin uploads a `.docx` with `{{placeholders}}`, or uses AI to generate both the document and interview from a prompt.  
2. **Interview Completion**: Staff fills out the HTML form (interview) for an active template, producing an answerset.  
3. **Document Generation**: The answerset is merged with the template via `docxtpl` to produce a completed `.docx`, optionally converted to `.pdf` via LibreOffice.  
4. **Approval**: Approvers can accept or reject submissions with a rejection reason.  
  
## Local Testing (Multi-Tenancy)  
  
```bash
cd backend
DATABASE_URL=sqlite:///docform.db uvicorn main:app --reload
```

In a separate terminal:
```bash
cd frontend
npm run dev
```

Then in browser:
- `http://demo.localhost:3000` → log in as `admin`/`admin123` (Tenant 1 — Demo Business)
- `http://girlguides.localhost:3000` → log in as `admin`/`admin123` (Tenant 2 — Girl Guides, same username different tenant)
- `http://admin.localhost:3000` → log in as `superadmin`/`super123` (manage tenants)
- `http://localhost:3000` → bare domain (placeholder/marketing — no login)

Each subdomain is a completely isolated environment. Tokens from one subdomain are rejected on another.
  
## Roadmap  
  
Planned architectural changes — not yet implemented:  
  
- **Database persistence**: Partially complete — user/tenant storage has been migrated to PostgreSQL with a repository abstraction (`backend/repositories/`). Templates and submissions still use flat-file JSON in `data/`.  
  
## Conventions  
  
- Interview schemas follow the format defined in `InterviewSchema.json`  
- Templates use `{{placeholder}}` syntax in `.docx` files  
- Default seed creates two tenants (demo, girlguides), a superadmin user, and admin/staff users per tenant
- Username uniqueness is per-tenant (same username can exist in different tenants)
