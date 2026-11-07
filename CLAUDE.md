# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Product

OncoFlow is a doctor-facing portal for managing follow-ups and scheduling for oncology patients, with a WhatsApp channel for patients. Goal: keep long-term patients engaged with care and catch missed follow-ups before patients are lost to care. See `docs/need.txt` for the full brief and `README.md` for run instructions.

## Commands

Backend (`server/`, FastAPI + SQLAlchemy, **PostgreSQL**):
```bash
cd server
bash scripts/setup_db.sh                     # one-time: create pg role + db (needs sudo)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seed.py                               # create tables + load data into Postgres
uvicorn app.main:app --reload --port 8000    # API + Swagger at /docs
```

Frontend (`web/`, Next.js 14 App Router + Tailwind):
```bash
cd web
npm install
npm run dev      # http://localhost:3000
npm run build    # production build (also the type/lint check)
npm run lint
```

Demo login: `kiran@oncoflow.health` / `oncoflow`.

## Architecture

**Backend** follows a standard FastAPI layout:
- `app/config.py` — env-driven settings (`pydantic-settings`). Defaults to SQLite so the demo runs with no setup; `DATABASE_URL` switches to Postgres.
- `app/clients.py` — external clients. `WhatsAppClient` wraps Twilio and **falls back to mock mode** (logs instead of sends) when Twilio creds are absent, so the app always runs. Supports both Account-SID+Auth-Token and API-Key auth.
- `app/database.py` / `app/models.py` — engine/session and ORM models (Doctor, Patient, FollowUp, Message, Note).
- `app/services/` — business logic. `scheduling.py` enforces conflict-free booking and suggests open slots within clinic hours; `messaging.py` classifies inbound WhatsApp messages (symptom/feedback/general) and files them under the matching patient by phone.
- `app/routes/` — thin HTTP layer (`patients`, `followups`, `messages`, `dashboard`). `messages.py` has the Twilio inbound webhook at `POST /api/messages/webhook`.
- `seed.py` — synthetic, clinically-plausible oncology data. Tumour choice respects patient sex.

**Frontend** (`web/app/`, App Router, all pages are client components):
- `components/AppShell.tsx` wraps every page: it is the client-side auth guard (redirects to `/login` when not authed) and renders the macOS-window chrome + `Sidebar`. `/login` renders outside the shell.
- `lib/api.ts` — typed fetch client; base URL from `NEXT_PUBLIC_API_BASE` (default `http://localhost:8000`).
- `lib/auth.ts` — **demo-only** localStorage auth (no real session; gates the UI only).
- `lib/ui.tsx` — shared pills/avatars/time formatting; `components/icons.tsx` — inline SVG icon set.
- Pages mirror the sidebar: dashboard (`page.tsx`), `patients/` (+ `[id]` detail with timeline/follow-ups/WhatsApp/notes tabs), `schedule/` (conflict-free booking UI), `messages/` (WhatsApp inbox), `oncology/{treatment,imaging,safety}`, `analytics/`, `settings/`.

## Design

UI must match `ui_samples/Dashboard-UI.webp` — premium macOS look: grouped sidebar with a purple (`brand-500` = `#635bff`) active item, big greeting header, hero metric card with area chart, status banner, four stat cards, colored quick-action tiles. Inter font (loaded via CSS `@import` in `globals.css`, **not** `next/font` — the build environment has no network to Google Fonts).

## Constraints

- **Synthetic data only** — never commit real patient records.
- The **35% follow-up uplift** from the brief is a demo target, not clinically validated. It is labelled as such in the UI; keep it that way.
- Twilio needs an **Account SID** (`AC...`) to actually send; only an API key is configured in `server/.env`, so it stays in mock mode until that's added.
- `pip` on this machine's Python 3.14 can't build older pinned wheels (`psycopg2-binary`, pinned `pydantic`); `requirements.txt` is intentionally loose and uses `psycopg` (v3) for Postgres.
