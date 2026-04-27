# DocForm

A document form platform for generating filled Word (.docx) and PDF documents from templates — built with **FastAPI** (Python) and **React**.

---

## Features

- **Upload Word templates** with `{{placeholder}}` tags — fields auto-detected
- **Visual field editor** — configure type, label, required, dropdown options per field
- **HotDoc-style multi-step form** for staff filling out submissions
- **Generates .docx** immediately on submission via `docxtpl`
- **Generates PDF** if LibreOffice is installed on the server
- **Role-based access** — Admin, Staff, Approver
- **Approve / Reject workflow** with reason tracking
- **PostgreSQL database** for user storage (JSON file backend also available via config)

---

## Quick Start

### Docker (recommended)

```bash
cp backend/.env.example backend/.env
# Edit .env with your API keys
docker compose up --build
```

This starts PostgreSQL, the backend API, and the frontend. The app is available at **http://localhost:3000**.

### Manual Setup

#### 1. Database

Start a PostgreSQL instance (e.g. via Docker):

```bash
docker run -d --name docform-db -e POSTGRES_USER=docform -e POSTGRES_PASSWORD=docform -e POSTGRES_DB=docform -p 5432:5432 postgres:16-alpine
```

Alternatively, set `STORAGE_BACKEND=json` in `backend/.env` to skip the database requirement and use flat-file JSON storage instead.

#### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Backend runs at **http://localhost:8000**
API docs at **http://localhost:8000/docs**

#### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:3000**

---

## Default Credentials

| Username   | Password     | Role     | Can do                              |
|------------|--------------|----------|-------------------------------------|
| `admin`    | `admin123`   | Admin    | Upload templates, edit fields, all  |
| `staff`    | `staff123`   | Staff    | Fill forms, download own docs       |
| `approver` | `approver123`| Approver | View all, approve/reject            |

Change these via the admin user management UI or API after first run.

---

## Configuration

Key environment variables (set in `backend/.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `STORAGE_BACKEND` | `db` | `"db"` for PostgreSQL, `"json"` for flat-file JSON |
| `DATABASE_URL` | `postgresql://docform:docform@db:5432/docform` | PostgreSQL connection string (used when `STORAGE_BACKEND=db`) |
| `OPENAI_API_KEY` | — | OpenAI API key for AI template generation |
| `GEMINI_KEY` | — | Google Gemini API key |
| `DEVIN_KEY` | — | Devin API key |

---

## User Management

Admins can manage users via the REST API:

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/users` | List all users |
| `POST` | `/api/users` | Create a new user |
| `PUT` | `/api/users/{id}` | Update user fields |
| `DELETE` | `/api/users/{id}` | Delete a user |

All endpoints require admin authentication (Bearer token).

---

## Creating a Template

1. Create a Word document (.docx)
2. Add `{{placeholder}}` tags where you want data inserted, e.g.:
   ```
   This agreement is between {{company_name}} and {{client_name}},
   dated {{contract_date}}, for the sum of £{{amount}}.
   ```
3. Log in as **admin** → Templates → New template → upload the .docx
4. Fields are auto-detected. Go to **Edit fields** to set types, labels, and options.
5. Activate the template — staff can now fill it in

---

## PDF Generation

PDF output requires **LibreOffice** on the server:

```bash
# Ubuntu / Debian
sudo apt install libreoffice

# macOS
brew install --cask libreoffice

# Windows
# Download from https://www.libreoffice.org/download/
```

If LibreOffice is not installed, `.docx` download still works. The PDF button will be greyed out.

---

## Project Structure

```
docform/
├── docker-compose.yml          # Orchestrates db, backend, frontend services
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── auth_utils.py           # JWT auth, password hashing, role guards
│   ├── config.py               # Pydantic settings (env vars)
│   ├── models.py               # SQLAlchemy ORM models
│   ├── requirements.txt
│   ├── alembic/                # Database migrations
│   │   ├── env.py
│   │   └── versions/
│   ├── repositories/           # User storage abstraction
│   │   ├── base.py             # Abstract UserRepository
│   │   ├── json_repo.py        # JSON file implementation
│   │   ├── db_repo.py          # PostgreSQL implementation
│   │   └── factory.py          # Factory to select backend
│   ├── routes/
│   │   ├── auth.py             # Login, /me
│   │   ├── templates.py        # Upload, list, edit, delete templates
│   │   ├── submissions.py      # Create, list, approve, download
│   │   └── users.py            # User CRUD (admin only)
│   ├── data/
│   │   ├── templates/          # Template metadata JSON files
│   │   └── submissions/        # Submission JSON files
│   └── uploads/
│       ├── templates/          # Uploaded .docx template files
│       └── generated/          # Generated .docx and .pdf outputs
│
└── frontend/
    ├── src/
    │   ├── App.jsx             # Routes
    │   ├── api.js              # Axios instance
    │   ├── context/
    │   │   └── AuthContext.jsx
    │   ├── pages/
    │   │   ├── LoginPage.jsx
    │   │   ├── DashboardPage.jsx
    │   │   ├── TemplatesPage.jsx
    │   │   ├── TemplateEditPage.jsx
    │   │   ├── NewSubmissionPage.jsx
    │   │   ├── SubmissionsPage.jsx
    │   │   └── SubmissionDetailPage.jsx
    │   └── components/
    │       └── shared/
    │           └── Layout.jsx
    ├── package.json
    └── vite.config.js
```

---

## Security Notes (production)

- Change `SECRET_KEY` in `auth_utils.py` to a long random string
- Hash passwords properly (bcrypt already used — just change the plaintext defaults)
- Run behind HTTPS
- Set `allow_origins` in `main.py` to your actual domain
