# OncoFlow

A doctor-facing portal that keeps **oncology patients connected across their care
journey** — early identification of patients needing follow-up, WhatsApp engagement,
and conflict-free scheduling, in one premium workspace for care teams.

Built for the Health-a-thon 2026 brief (see `docs/need.txt`).

## What's inside

| Pillar                                                                                                            | Where                                                      |
| ----------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| Doctor dashboard with grouped side panels                                                                         | `web/` (Next.js)                                           |
| WhatsApp follow-ups via Twilio (inbound auto-filed under the patient, classified as symptom / feedback / general) | `server/app/services/messaging.py`, `routes/messages.py`   |
| Conflict-free follow-up scheduling (open-slot suggestions, overlap prevention)                                    | `server/app/services/scheduling.py`, `routes/followups.py` |
| Oncology-specific views (Treatment Tracker, Imaging & Restaging, Safety & Toxicity)                               | `web/app/oncology/*`                                       |
| Interoperability / HMS import                                                                                     | stubbed in Settings (roadmap)                              |

## Stack

- **Backend:** FastAPI + SQLAlchemy (`server/`), **PostgreSQL** database.
- **Auth:** real users table, register/login, PBKDF2-hashed passwords, JWT tokens.
- **Frontend:** Next.js 14 (App Router) + Tailwind, Inter font (`web/`).
- **Messaging:** Twilio WhatsApp (mock mode until an Account SID is set).

## Run it locally

### 1. Database (PostgreSQL)

Create the role and database (one time; needs the `postgres` superuser):

```bash
cd server
bash scripts/setup_db.sh          # creates role + db 'oncoflow'
# or manually:
# sudo -u postgres psql -c "CREATE ROLE oncoflow LOGIN PASSWORD 'oncoflow';" \
#                        -c "CREATE DATABASE oncoflow OWNER oncoflow;"
```

The connection string lives in `server/.env`
(`DATABASE_URL=postgresql+psycopg://oncoflow:oncoflow@localhost:5432/oncoflow`).

### 2. Backend (port 8000)

```bash
cd server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seed.py          # creates tables + loads oncology data into Postgres
uvicorn app.main:app --reload --port 8000
```

API docs at http://localhost:8000/docs

### 3. Frontend (port 3000)

```bash
cd web
npm install
npm run dev
```

Open http://localhost:3000 → you land on the **login page**.

## Database

PostgreSQL, configured via `DATABASE_URL` in `server/.env`. `python seed.py`
creates all tables (`users`, `patients`, `followups`, `messages`, `notes`, …)
and loads the demo clinician + oncology patient data.

## WhatsApp / Twilio

`server/.env` is pre-filled with the provided API Key SID + Secret. To send real
messages you also need your **Account SID** (starts with `AC`):

```
TWILIO_ACCOUNT_SID=AC...
```

Until then the app runs in **mock mode** — outbound messages are logged, and the
inbound webhook still files patient replies. Point your Twilio WhatsApp sandbox
webhook at `POST http://<host>:8000/api/messages/webhook`.

## Deployment (Vercel + Render)

This stack deploys cleanly with the **frontend on Vercel** and the **backend + Postgres on Render**. Deploying also fixes WhatsApp inbound: Render gives the API a public HTTPS URL, so you point Twilio's webhook straight at it (no ngrok).

### 1. Backend + database on Render

- Push this repo to GitHub, then in Render: **New > Blueprint** and select the repo. `render.yaml` provisions the `oncoflow-api` web service and a `oncoflow-db` Postgres instance; `DATABASE_URL` is wired automatically.
- Set these env vars in the Render dashboard (marked `sync: false`): `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `SARVAM_API_KEY`, and `CORS_ORIGINS` = your Vercel URL (e.g. `https://oncoflow.vercel.app`).
- Tables and the `kiran@oncoflow.health` login are created automatically on first boot (non-destructive; restarts never wipe data).

### 2. Frontend on Vercel

- In Vercel: **New Project** → import the repo → set **Root Directory** to `web`.
- Add env var `NEXT_PUBLIC_API_BASE` = your Render API URL (e.g. `https://oncoflow-api.onrender.com`).
- Deploy. (Next.js is auto-detected.)

### 3. Twilio WhatsApp webhook

- In the Twilio WhatsApp sandbox, set **"When a message comes in"** to
  `https://<your-api>.onrender.com/api/messages/webhook`.
- Join the sandbox from the patient's phone, and the inbound → AI reply → symptom-capture loop works without any tunnel.

Notes: Render's free web service sleeps when idle (first request after a cold start is slow), and `DATABASE_URL` in `postgres://` form is normalized to the `psycopg` driver automatically.
