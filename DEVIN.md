# Docform — Devin Context  
  
> **Last verified**: 2026-04-09  
>  
> **Maintenance rule**: When any Devin session makes a structural or architectural change to this project (new storage backend, new modules, changed workflows, new concepts), update this file as part of that same task. Keep descriptions high-level — focus on *what* and *where*, not implementation detail.  
  
## What is Docform?  
  
Docform is a system for the creation, use, and management of **document templates**. It is built with FastAPI (Python) and React (JavaScript).  
  
## Core Concepts  
  
- **Document Template**: A Word (.docx) document containing `{{placeholder}}` tags that mark where answers will be inserted. Templates are uploaded or AI-generated.  
  
- **Interview**: A set of questions, defined in a standardised JSON format (`InterviewSchema.json`), associated with a document template. Interviews are presented to users as HTML forms in the React frontend. Each question corresponds to one or more placeholders in the template.  
  
- **Answerset**: The result of completing (or partially completing) an interview. Answersets capture the user's responses. They are used to populate a completed instance of the associated document template, and are stored for subsequent re-use or deletion.  
  
- **Completed Instance**: A rendered `.docx` (and optionally `.pdf`) document produced by merging an answerset with its document template.  
  
## Architecture  
  
- **Backend**: FastAPI app in `backend/main.py` with routers under `backend/routes/`:  
  - `auth.py` — JWT-based authentication (admin, staff, approver roles)  
  - `templates.py` — Template CRUD, upload, field configuration, AI generation  
  - `submissions.py` — Submission creation, document rendering, approval workflow  
- **Frontend**: React SPA (Vite + Tailwind CSS) in `frontend/`  
- **Storage**: Currently flat-file JSON in `data/` and binary files in `uploads/` — no external database (see Roadmap)  
- **AI Generation**: OpenAI and Google Gemini integration for generating templates and interviews from natural language prompts  
  
## Key Workflows  
  
1. **Template Creation**: Admin uploads a `.docx` with `{{placeholders}}`, or uses AI to generate both the document and interview from a prompt.  
2. **Interview Completion**: Staff fills out the HTML form (interview) for an active template, producing an answerset.  
3. **Document Generation**: The answerset is merged with the template via `docxtpl` to produce a completed `.docx`, optionally converted to `.pdf` via LibreOffice.  
4. **Approval**: Approvers can accept or reject submissions with a rejection reason.  
  
## Roadmap  
  
Planned architectural changes — not yet implemented:  
  
- **Database persistence**: Replace flat-file JSON storage (`data/`) with a relational database. When this is implemented, update the "Storage" line in the Architecture section above and adjust any references to `data/` paths.  
  
- **Multi-tenancy**: Introduce a tenancy system so different groups of users are entirely isolated from each other (separate templates, interviews, answersets, and users per tenant). When this is implemented, add "Tenant" to the Core Concepts section above and describe the isolation model.  
  
## Conventions  
  
- Interview schemas follow the format defined in `InterviewSchema.json`  
- Templates use `{{placeholder}}` syntax in `.docx` files  
- Default users (admin/staff/approver) are seeded on first startup if `data/users.json` doesn't exist