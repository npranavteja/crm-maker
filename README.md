# SponsorFlow CRM  API Reference

## Setup

```bash
pip install fastapi uvicorn sqlalchemy
uvicorn main:app --reload
```

Base URL: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`  
DB: SQLite (`crm.db`, auto-created on first run)

---

## Sponsors

### Fields
| Field | Type | Values |
|---|---|---|
| company | string | required |
| contact | string | required |
| role | string | |
| email | string | |
| phone | string | |
| linkedin | string | |
| amount | int | rupees |
| priority | string | `high` / `medium` / `low` |
| stage | string | `prospecting` / `outreach` / `negotiation` / `contracted` / `closed` |
| category | string | e.g. `Auto / EV`, `Tech`, `Finance` |
| tags | string | comma-separated, e.g. `"ev,csr,tier1"` |

### Endpoints

**List sponsors**
```
GET /sponsors
```
Query params: `stage`, `category`, `priority`, `search`, `sort_by`, `sort_dir`, `skip`, `limit`
```bash
curl "http://localhost:8000/sponsors?stage=negotiation&sort_by=amount&sort_dir=desc"
curl "http://localhost:8000/sponsors?search=bosch&limit=10"
```

**Create sponsor**
```
POST /sponsors
```
```bash
curl -X POST http://localhost:8000/sponsors \
  -H "Content-Type: application/json" \
  -d '{"company":"Bosch India","contact":"Rajan Mehta","role":"CSR Manager","email":"rajan@bosch.in","amount":150000,"stage":"outreach","category":"Auto / EV","priority":"high","tags":"auto,ev,csr"}'
```

**Get full sponsor profile** (includes activities, notes, tasks)
```
GET /sponsors/{id}
```

**Update sponsor**
```
PATCH /sponsors/{id}
```
```bash
curl -X PATCH http://localhost:8000/sponsors/1 \
  -H "Content-Type: application/json" \
  -d '{"stage":"negotiation","amount":200000}'
```
Stage changes are auto-logged to activity feed.

**Delete sponsor**
```
DELETE /sponsors/{id}
```

**Bulk move stage**
```
POST /sponsors/bulk-stage
```
```bash
curl -X POST http://localhost:8000/sponsors/bulk-stage \
  -H "Content-Type: application/json" \
  -d '{"sponsor_ids":[1,2,3],"stage":"outreach"}'
```

---

## Pipeline

**Kanban view** — all stages, counts, and totals
```
GET /pipeline
```
Returns each stage with `count`, `total` (value), and `sponsors` array.

---

## Metrics

```
GET /metrics
```
Returns:
- `total_pipeline` — sum of all active (non-closed) deals
- `contracted_value` — sum of contracted deals
- `active_count` — non-closed sponsor count
- `win_rate` — contracted / total (%)
- `avg_deal_size`
- `tasks_pending`, `tasks_overdue`
- `by_category` — value breakdown per category
- `by_stage` — count + value per stage

---

## Activities

Auto-logged on: sponsor created, stage changed, task completed, note added, email drafted.

**List activity feed**
```
GET /activities
```
Query params: `sponsor_id`, `action`

Action types: `created`, `stage_change`, `task_done`, `note_added`, `email_drafted`, or any custom string.

**Log manual activity**
```
POST /activities
```
```bash
curl -X POST http://localhost:8000/activities \
  -H "Content-Type: application/json" \
  -d '{"sponsor_id":1,"action":"call","note":"Spoke to Rajan, positive response, follow up Fri"}'
```

---

## Email Templates

### Placeholders
Use these in `subject` or `body` — auto-replaced when filling:
- `[Name]` — contact name
- `[Company]` — company name
- `[Role]` — contact role
- `[Amount]` — deal amount
- `[Category]` — category

**List templates**
```
GET /templates?category=Auto
```

**Create template**
```
POST /templates
```
```bash
curl -X POST http://localhost:8000/templates \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Cold outreach — auto sector",
    "subject": "Agnirath Solar Car — Partnership with [Company]",
    "body": "Hi [Name],\n\nI am reaching out from Agnirath, IIT Madras'\''s solar car team...\n\nBest,\nAgnirath Team",
    "category": "Auto / EV"
  }'
```

**Fill template for a sponsor** (merges placeholders)
```
POST /templates/fill
```
```bash
curl -X POST http://localhost:8000/templates/fill \
  -H "Content-Type: application/json" \
  -d '{"sponsor_id":1,"template_id":2}'
```
Returns filled `subject` + `body`. Auto-logs `email_drafted` to activity.

**Update / Delete template**
```
PATCH /templates/{id}
DELETE /templates/{id}
```

---

## Tasks

Track follow-ups, calls, deadlines per sponsor.

**List tasks**
```
GET /tasks
```
Query params: `sponsor_id`, `done` (true/false), `overdue` (true)
```bash
curl "http://localhost:8000/tasks?done=false&overdue=true"
```

**Create task**
```
POST /tasks
```
```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"sponsor_id":1,"title":"Follow up call with Rajan","due_date":"2025-07-01","priority":"high"}'
```

**Mark done / update**
```
PATCH /tasks/{id}
```
```bash
curl -X PATCH http://localhost:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"done":true}'
```
Marking done auto-logs to activity feed.

**Delete task**
```
DELETE /tasks/{id}
```

---

## Notes

Free-form notes per sponsor.

**List notes**
```
GET /notes?sponsor_id=1
```

**Add note**
```
POST /notes
```
```bash
curl -X POST http://localhost:8000/notes \
  -H "Content-Type: application/json" \
  -d '{"sponsor_id":1,"body":"Rajan mentioned budget finalises in August. Revisit then."}'
```

**Delete note**
```
DELETE /notes/{id}
```

---

## Reminders

**Upcoming + overdue tasks**
```
GET /reminders?days=7
```
Returns `upcoming` (within N days) and `overdue` (past due, not done).

---

## Global Search

Searches sponsors (company, contact, email, tags), templates, and notes.
```
GET /search?q=bosch
```

---

## Typical Workflow

```
1. POST /sponsors           — add prospect
2. POST /templates          — create outreach email template
3. POST /templates/fill     — generate filled email for that sponsor
4. POST /activities         — log "email sent"
5. POST /tasks              — set follow-up reminder
6. PATCH /sponsors/{id}     — move to next stage after response
7. GET /reminders           — check what's due today
8. GET /metrics             — review pipeline health
```
