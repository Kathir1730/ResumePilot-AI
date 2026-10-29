# ResumePilot AI

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Kathir1730/ResumePilot-AI)

**AI-assisted resume tailoring with transparent, human-approved edits.**

Upload a resume and a job description, review suggested edits side by side, and approve or reject each change before exporting.

## Features
- Account registration and login (development JWT implementation)
- Upload PDF, DOCX, or TXT resumes
- Paste a job description and save projects
- OpenAI-compatible Chat Completions integration
- Per-change rationale and pending/approved/rejected states
- Original and proposed wording shown side by side
- Export PDF and DOCX using approved replacements only
- SQLite locally and PostgreSQL configuration for deployment

## Stack
- Frontend: React, TypeScript, Vite
- Backend: Python, FastAPI
- Database: SQLAlchemy
- Parsing/export: PyMuPDF, python-docx, ReportLab

## Run locally

Requirements: Python 3.11+ and Node.js 20+.

### Backend
```bash
cd backend
python -m venv .venv
```
Activate the environment on Windows PowerShell:
```powershell
.venv\Scripts\Activate.ps1
```
Then:
```bash
pip install -r requirements.txt
```
Copy `backend/.env.example` to `backend/.env`, set a strong random `JWT_SECRET`, and optionally configure `OPENAI_API_KEY`. Keep real secrets out of GitHub.

Start from the `backend` folder:
```bash
uvicorn app.main:app --reload
```
Health check: http://127.0.0.1:8000/health

### Frontend
Open a second terminal:
```bash
cd frontend
npm install
```
Copy `frontend/.env.example` to `frontend/.env` and set:
```env
VITE_API_BASE=http://127.0.0.1:8000
```
Run:
```bash
npm run dev
```
Open the local Vite URL shown in the terminal, usually http://localhost:5173.

Without an LLM API key, the backend returns an explicitly labeled demo placeholder; it does not perform real tailoring.

## Deploy
Use the **Deploy to Render** button at the top to review and deploy the Blueprint resources. GitHub stores the code; it does not run the full-stack app by itself.
- Backend: Render (FastAPI and PostgreSQL)
- Frontend: Vercel (set Root Directory to `frontend` and `VITE_API_BASE` to the deployed backend URL)
- Set the backend's `FRONTEND_ORIGIN` to the exact deployed frontend origin.
- Store `OPENAI_API_KEY` only in backend hosting environment settings, never in frontend variables.

## Limitations and safety
This is an early portfolio MVP, not a production-ready service. AI suggestions must be reviewed for accuracy. The current export rebuilds a document from extracted text and does not preserve the original resume's layout. Authentication, file handling, data retention, rate limiting, and privacy protections need further security review before real personal resumes are used. Do not commit `.env` files or API keys.
