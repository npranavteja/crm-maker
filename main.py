from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from database import get_db, init_db
from models import Sponsor, Activity, Template, Task, Note

app = FastAPI(title="SponsorFlow CRM")

@app.on_event("startup")
def startup():
    init_db()

class SponsorIn(BaseModel):
    company: str
    contact: str
    role: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    amount: Optional[int] = 0
    priority: Optional[str] = "medium"
    stage: Optional[str] = "prospecting"
    category: Optional[str] = None
    tags: Optional[str] = None

class SponsorUpdate(BaseModel):
    company: Optional[str] = None
    contact: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    amount: Optional[int] = None
    priority: Optional[str] = None
    stage: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None

class ActivityIn(BaseModel):
    sponsor_id: int
    action: str
    note: Optional[str] = None

class TemplateIn(BaseModel):
    title: str
    subject: str
    body: str
    category: Optional[str] = None

class TaskIn(BaseModel):
    sponsor_id: int
    title: str
    due_date: Optional[str] = None
    priority: Optional[str] = "medium"

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    done: Optional[bool] = None

class NoteIn(BaseModel):
    sponsor_id: int
    body: str

class BulkStageIn(BaseModel):
    sponsor_ids: List[int]
    stage: str

class TemplateFillIn(BaseModel):
    sponsor_id: int
    template_id: int

@app.get("/sponsors")
def list_sponsors(
    stage: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_dir: Optional[str] = "desc",
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    q = db.query(Sponsor)
    if stage:
        q = q.filter(Sponsor.stage == stage)
    if category:
        q = q.filter(Sponsor.category == category)
    if priority:
        q = q.filter(Sponsor.priority == priority)
    if search:
        term = f"%{search}%"
        q = q.filter(or_(Sponsor.company.ilike(term), Sponsor.contact.ilike(term), Sponsor.email.ilike(term)))
    col = getattr(Sponsor, sort_by, Sponsor.created_at)
    q = q.order_by(col.desc() if sort_dir == "desc" else col.asc())
    total = q.count()
    items = q.offset(skip).limit(limit).all()
    return {"total": total, "items": items}

@app.post("/sponsors", status_code=201)
def create_sponsor(s: SponsorIn, db: Session = Depends(get_db)):
    obj = Sponsor(**s.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    db.add(Activity(sponsor_id=obj.id, action="created", note=f"Added {obj.company}"))
    db.commit()
    return obj

@app.get("/sponsors/{id}")
def get_sponsor(id: int, db: Session = Depends(get_db)):
    obj = db.query(Sponsor).filter(Sponsor.id == id).first()
    if not obj:
        raise HTTPException(404)
    activities = db.query(Activity).filter(Activity.sponsor_id == id).order_by(Activity.created_at.desc()).all()
    notes = db.query(Note).filter(Note.sponsor_id == id).order_by(Note.created_at.desc()).all()
    tasks = db.query(Task).filter(Task.sponsor_id == id).order_by(Task.due_date.asc()).all()
    return {"sponsor": obj, "activities": activities, "notes": notes, "tasks": tasks}

@app.patch("/sponsors/{id}")
def update_sponsor(id: int, s: SponsorUpdate, db: Session = Depends(get_db)):
    obj = db.query(Sponsor).filter(Sponsor.id == id).first()
    if not obj:
        raise HTTPException(404)
    old_stage = obj.stage
    for k, v in s.dict(exclude_none=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    if s.stage and s.stage != old_stage:
        db.add(Activity(sponsor_id=id, action="stage_change", note=f"{old_stage} → {s.stage}"))
        db.commit()
    return obj

@app.delete("/sponsors/{id}", status_code=204)
def delete_sponsor(id: int, db: Session = Depends(get_db)):
    obj = db.query(Sponsor).filter(Sponsor.id == id).first()
    if not obj:
        raise HTTPException(404)
    db.delete(obj)
    db.commit()

@app.post("/sponsors/bulk-stage")
def bulk_stage(b: BulkStageIn, db: Session = Depends(get_db)):
    updated = 0
    for sid in b.sponsor_ids:
        obj = db.query(Sponsor).filter(Sponsor.id == sid).first()
        if obj:
            old = obj.stage
            obj.stage = b.stage
            db.add(Activity(sponsor_id=sid, action="stage_change", note=f"{old} → {b.stage}"))
            updated += 1
    db.commit()
    return {"updated": updated}

@app.get("/pipeline")
def pipeline(db: Session = Depends(get_db)):
    stages = ["prospecting", "outreach", "negotiation", "contracted", "closed"]
    result = {}
    for stage in stages:
        sponsors = db.query(Sponsor).filter(Sponsor.stage == stage).all()
        result[stage] = {
            "count": len(sponsors),
            "total": sum(s.amount for s in sponsors),
            "sponsors": sponsors
        }
    return result

@app.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    all_s = db.query(Sponsor).all()
    contracted = [s for s in all_s if s.stage == "contracted"]
    active = [s for s in all_s if s.stage not in ("closed",)]
    tasks_due = db.query(Task).filter(Task.done == False).count()
    overdue = db.query(Task).filter(
        Task.done == False,
        Task.due_date < datetime.utcnow().date().isoformat()
    ).count()
    by_cat = {}
    for s in all_s:
        if s.category:
            by_cat[s.category] = by_cat.get(s.category, 0) + s.amount
    by_stage = {stage: {"count": 0, "value": 0} for stage in ["prospecting","outreach","negotiation","contracted","closed"]}
    for s in all_s:
        if s.stage in by_stage:
            by_stage[s.stage]["count"] += 1
            by_stage[s.stage]["value"] += s.amount
    return {
        "total_pipeline": sum(s.amount for s in active),
        "contracted_value": sum(s.amount for s in contracted),
        "active_count": len(active),
        "total_sponsors": len(all_s),
        "win_rate": round(len(contracted) / len(all_s) * 100, 1) if all_s else 0,
        "avg_deal_size": round(sum(s.amount for s in all_s) / len(all_s)) if all_s else 0,
        "tasks_pending": tasks_due,
        "tasks_overdue": overdue,
        "by_category": by_cat,
        "by_stage": by_stage
    }

@app.get("/activities")
def list_activities(sponsor_id: Optional[int] = None, action: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Activity).order_by(Activity.created_at.desc())
    if sponsor_id:
        q = q.filter(Activity.sponsor_id == sponsor_id)
    if action:
        q = q.filter(Activity.action == action)
    return q.limit(100).all()

@app.post("/activities", status_code=201)
def log_activity(a: ActivityIn, db: Session = Depends(get_db)):
    obj = Activity(**a.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@app.get("/templates")
def list_templates(category: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Template)
    if category:
        q = q.filter(Template.category == category)
    return q.all()

@app.post("/templates", status_code=201)
def create_template(t: TemplateIn, db: Session = Depends(get_db)):
    obj = Template(**t.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@app.get("/templates/{id}")
def get_template(id: int, db: Session = Depends(get_db)):
    obj = db.query(Template).filter(Template.id == id).first()
    if not obj:
        raise HTTPException(404)
    return obj

@app.patch("/templates/{id}")
def update_template(id: int, t: TemplateIn, db: Session = Depends(get_db)):
    obj = db.query(Template).filter(Template.id == id).first()
    if not obj:
        raise HTTPException(404)
    for k, v in t.dict().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

@app.delete("/templates/{id}", status_code=204)
def delete_template(id: int, db: Session = Depends(get_db)):
    obj = db.query(Template).filter(Template.id == id).first()
    if not obj:
        raise HTTPException(404)
    db.delete(obj)
    db.commit()

@app.post("/templates/fill")
def fill_template(data: TemplateFillIn, db: Session = Depends(get_db)):
    t = db.query(Template).filter(Template.id == data.template_id).first()
    s = db.query(Sponsor).filter(Sponsor.id == data.sponsor_id).first()
    if not t or not s:
        raise HTTPException(404)
    replacements = {
        "[Name]": s.contact or "",
        "[Company]": s.company or "",
        "[Role]": s.role or "",
        "[Amount]": str(s.amount) if s.amount else "",
        "[Category]": s.category or "",
    }
    subject = t.subject
    body = t.body
    for k, v in replacements.items():
        subject = subject.replace(k, v)
        body = body.replace(k, v)
    db.add(Activity(sponsor_id=s.id, action="email_drafted", note=f"Template '{t.title}' filled"))
    db.commit()
    return {"subject": subject, "body": body, "sponsor": s.company, "template": t.title}

@app.get("/tasks")
def list_tasks(
    sponsor_id: Optional[int] = None,
    done: Optional[bool] = None,
    overdue: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    q = db.query(Task)
    if sponsor_id:
        q = q.filter(Task.sponsor_id == sponsor_id)
    if done is not None:
        q = q.filter(Task.done == done)
    if overdue:
        q = q.filter(Task.done == False, Task.due_date < datetime.utcnow().date().isoformat())
    return q.order_by(Task.due_date.asc()).all()

@app.post("/tasks", status_code=201)
def create_task(t: TaskIn, db: Session = Depends(get_db)):
    obj = Task(**t.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@app.patch("/tasks/{id}")
def update_task(id: int, t: TaskUpdate, db: Session = Depends(get_db)):
    obj = db.query(Task).filter(Task.id == id).first()
    if not obj:
        raise HTTPException(404)
    for k, v in t.dict(exclude_none=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    if t.done:
        s = db.query(Sponsor).filter(Sponsor.id == obj.sponsor_id).first()
        db.add(Activity(sponsor_id=obj.sponsor_id, action="task_done", note=f"Task completed: {obj.title}"))
        db.commit()
    return obj

@app.delete("/tasks/{id}", status_code=204)
def delete_task(id: int, db: Session = Depends(get_db)):
    obj = db.query(Task).filter(Task.id == id).first()
    if not obj:
        raise HTTPException(404)
    db.delete(obj)
    db.commit()

@app.get("/notes")
def list_notes(sponsor_id: int, db: Session = Depends(get_db)):
    return db.query(Note).filter(Note.sponsor_id == sponsor_id).order_by(Note.created_at.desc()).all()

@app.post("/notes", status_code=201)
def create_note(n: NoteIn, db: Session = Depends(get_db)):
    obj = Note(**n.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    db.add(Activity(sponsor_id=n.sponsor_id, action="note_added", note=n.body[:80]))
    db.commit()
    return obj

@app.delete("/notes/{id}", status_code=204)
def delete_note(id: int, db: Session = Depends(get_db)):
    obj = db.query(Note).filter(Note.id == id).first()
    if not obj:
        raise HTTPException(404)
    db.delete(obj)
    db.commit()

@app.get("/reminders")
def get_reminders(days: int = 7, db: Session = Depends(get_db)):
    cutoff = (datetime.utcnow() + timedelta(days=days)).date().isoformat()
    today = datetime.utcnow().date().isoformat()
    upcoming = db.query(Task).filter(
        Task.done == False,
        Task.due_date >= today,
        Task.due_date <= cutoff
    ).order_by(Task.due_date.asc()).all()
    overdue = db.query(Task).filter(
        Task.done == False,
        Task.due_date < today
    ).all()
    return {"upcoming": upcoming, "overdue": overdue}

@app.get("/search")
def search(q: str, db: Session = Depends(get_db)):
    term = f"%{q}%"
    sponsors = db.query(Sponsor).filter(
        or_(Sponsor.company.ilike(term), Sponsor.contact.ilike(term), Sponsor.email.ilike(term), Sponsor.tags.ilike(term))
    ).all()
    templates = db.query(Template).filter(
        or_(Template.title.ilike(term), Template.subject.ilike(term), Template.body.ilike(term))
    ).all()
    notes = db.query(Note).filter(Note.body.ilike(term)).all()
    return {"sponsors": sponsors, "templates": templates, "notes": notes}
