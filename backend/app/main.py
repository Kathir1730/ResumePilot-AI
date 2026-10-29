import os
from io import BytesIO
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from dotenv import load_dotenv
from .db import Base, engine, get_db
from .models import User, Project, Change
from .security import hash_password, verify_password, token_for, current_user
from .parser import parse
from .ai import generate
from .exports import render_text, docx_bytes, pdf_bytes
load_dotenv(); Base.metadata.create_all(bind=engine)
app = FastAPI(title="ResumePilot AI API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://127.0.0.1:5173"), "http://localhost:5173"], allow_origin_regex=r"https://.*\\.vercel\\.app", allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
class AuthIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
def get_project(pid, user, db):
    p = db.query(Project).filter_by(id=pid, user_id=user.id).first()
    if not p: raise HTTPException(404, "Resume project not found")
    return p
def output(p):
    return {"id":p.id, "title":p.title, "original_filename":p.filename, "original_text":p.original_text, "job_description":p.job_description, "changes":[{"id":c.id, "section":c.section, "original_text":c.original_text, "proposed_text":c.proposed_text, "rationale":c.rationale, "status":c.status} for c in sorted(p.changes, key=lambda x:x.id)]}
@app.get("/health")
def health(): return {"status":"ok"}
@app.post("/api/auth/register")
def register(x: AuthIn, db: Session = Depends(get_db)):
    email = x.email.lower().strip()
    if db.query(User).filter_by(email=email).first(): raise HTTPException(409, "Account already exists")
    u = User(email=email, password_hash=hash_password(x.password)); db.add(u); db.commit(); db.refresh(u)
    return {"token":token_for(u.id), "user":{"id":u.id, "email":u.email}}
@app.post("/api/auth/login")
def login(x: AuthIn, db: Session = Depends(get_db)):
    u = db.query(User).filter_by(email=x.email.lower().strip()).first()
    if not u or not verify_password(x.password, u.password_hash): raise HTTPException(401, "Invalid email or password")
    return {"token":token_for(u.id), "user":{"id":u.id, "email":u.email}}
@app.get("/api/projects")
def list_projects(db: Session = Depends(get_db), u: User = Depends(current_user)):
    return [{"id":p.id, "title":p.title, "original_filename":p.filename, "created_at":p.created_at.isoformat()} for p in db.query(Project).filter_by(user_id=u.id).order_by(Project.created_at.desc()).all()]
@app.post("/api/projects")
async def create(file: UploadFile = File(...), job_description: str = Form(...), title: str = Form("Resume tailored to job"), db: Session = Depends(get_db), u: User = Depends(current_user)):
    if len(job_description.strip()) < 30: raise HTTPException(422, "Job description must be at least 30 characters")
    filename, text = await parse(file)
    p = Project(user_id=u.id, title=title[:255], filename=filename, original_text=text, job_description=job_description.strip())
    db.add(p); db.commit(); db.refresh(p); return output(p)
@app.get("/api/projects/{pid}")
def get_one(pid: int, db: Session = Depends(get_db), u: User = Depends(current_user)): return output(get_project(pid, u, db))
@app.post("/api/projects/{pid}/generate")
async def generate_one(pid: int, db: Session = Depends(get_db), u: User = Depends(current_user)):
    p = get_project(pid, u, db)
    try: changes, mode = await generate(p.original_text, p.job_description)
    except Exception as e: raise HTTPException(502, "Suggestion generation failed. Check API configuration and try again.") from e
    for x in changes: db.add(Change(project_id=p.id, section=x["section"], original_text=x["original_text"], proposed_text=x["proposed_text"], rationale=x["rationale"], status="pending"))
    db.commit(); result = output(get_project(pid, u, db)); result["generation_mode"] = mode
    result["notice"] = "New suggestions are pending review. Original resume text is unchanged."
    return result
@app.post("/api/projects/{pid}/changes/{cid}/decision")
def decision(pid: int, cid: int, decision: str = Form(...), db: Session = Depends(get_db), u: User = Depends(current_user)):
    p = get_project(pid, u, db)
    if decision not in {"approved", "rejected"}: raise HTTPException(422, "Decision must be approved or rejected")
    c = db.query(Change).filter_by(id=cid, project_id=pid).first()
    if not c: raise HTTPException(404, "Change not found")
    c.status = decision; db.commit(); return output(get_project(pid, u, db))
@app.get("/api/projects/{pid}/export/{fmt}")
def export(pid: int, fmt: str, db: Session = Depends(get_db), u: User = Depends(current_user)):
    p = get_project(pid, u, db); text = render_text(p.original_text, p.changes)
    if fmt == "pdf": data, media = pdf_bytes(text), "application/pdf"
    elif fmt == "docx": data, media = docx_bytes(text), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else: raise HTTPException(404, "Format must be pdf or docx")
    return StreamingResponse(BytesIO(data), media_type=media, headers={"Content-Disposition":f'attachment; filename="resumepilot-approved-resume.{fmt}"'})
@app.delete("/api/projects/{pid}")
def delete(pid: int, db: Session = Depends(get_db), u: User = Depends(current_user)):
    p = get_project(pid, u, db); db.delete(p); db.commit(); return {"deleted":True}
