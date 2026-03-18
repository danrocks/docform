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
- **File-based storage** — no database required

---

## Quick Start

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Backend runs at **http://localhost:8000**
API docs at **http://localhost:8000/docs**

### 2. Frontend

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

Change these in `backend/data/users.json` after first run.

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
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── auth_utils.py        # JWT auth, password hashing, role guards
│   ├── requirements.txt
│   ├── routes/
│   │   ├── auth.py          # Login, /me
│   │   ├── templates.py     # Upload, list, edit, delete templates
│   │   └── submissions.py   # Create, list, approve, download
│   ├── data/
│   │   ├── users.json       # User accounts (auto-created)
│   │   ├── templates/       # Template metadata JSON files
│   │   └── submissions/     # Submission JSON files
│   └── uploads/
│       ├── templates/       # Uploaded .docx template files
│       └── generated/       # Generated .docx and .pdf outputs
│
└── frontend/
    ├── src/
    │   ├── App.jsx           # Routes
    │   ├── api.js            # Axios instance
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
