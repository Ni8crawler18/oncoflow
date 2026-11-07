## Product

OncoFlow is a doctor-facing portal for managing follow-ups and scheduling for oncology patients, with a **Telegram** channel for patients (an AI assistant, powered by Sarvam, chats with patients and captures symptoms). Goal: keep long-term patients engaged with care and catch missed follow-ups before patients are lost to care. See `docs/need.txt` for the brief and `README.md` for run instructions.

## Commands

Backend (`server/`, FastAPI + SQLAlchemy, **PostgreSQL**):
```bash
cd server
bash scripts/setup_db.sh                     # one-time: create pg role + db (needs sudo)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seed.py                               # create tables + load synthetic data into Postgres
uvicorn app.main:app --reload --port 8000    # API + Swagger at /docs
```
There is no automated test suite; `/docs` (Swagger) is the manual API harness. The app also creates tables and the default login on startup (see `app/main.py`), so `seed.py` is only needed to load demo patient data.

Frontend (`web/`, Next.js 14 App Router + Tailwind):
```bash
cd web
npm install
npm run dev      # http://localhost:3000
npm run build    # production build — also the type/lint check (run this to verify changes)
npm run lint
```

Demo login: `kiran@oncoflow.health` / `oncoflow` (created automatically on first backend boot when the users table is empty).

## Architecture

**Backend** (`server/app/`) is a standard FastAPI layout:
- `config.py` — env-driven settings (`pydantic-settings`). **Defaults to Postgres**; `normalized_database_url` rewrites Render's `postgres://` form to the `postgresql+psycopg` (psycopg v3) driver. Holds Meta WhatsApp, Telegram, Sarvam, JWT, and CORS config.
- `database.py` / `models.py` — engine/session and ORM models: `User` (auth), `Doctor`, `Patient`, `FollowUp`, `Message`, `Symptom`, `Note`. `Patient.telegram_chat_id` links a patient to their Telegram chat.
- `security.py` + `routes/auth.py` — real auth: register/login, stdlib **PBKDF2** password hashing, **JWT** (PyJWT) bearer tokens. `current_user` validates a token (`/api/auth/me`); **`current_doctor` is the guard most routes depend on** — it resolves the logged-in user to their `Doctor` row so **all patient data is scoped per doctor**.
- `clients.py` — external clients, each with a **mock fallback** (logs instead of calling) when creds are absent, so the app always runs:
  - `TelegramClient` — the live patient channel (Bot API: `sendMessage`, `setWebhook`).
  - `SarvamClient` — Sarvam AI chat completions (OpenAI-compatible) for the conversational assistant.
  - `WhatsAppClient` — Meta WhatsApp Cloud API; **legacy/secondary**, retained but not the active patient channel.
- `services/` — business logic:
  - `messaging.py` — Telegram linking + inbound handling: link a chat to a patient by MRN/phone, classify inbound (symptom/feedback/general), capture `Symptom` rows, auto-book from scheduling requests, and produce an AI reply. `DeliveryError` signals an unlinked patient.
  - `ai.py` — Sarvam-backed care assistant: proactive `generate_checkin`, contextual `generate_reply` (uses patient context + message history), and `analyze_symptom` (JSON triage). Everything degrades to keyword/template fallbacks when Sarvam is unconfigured.
  - `scheduling.py` — conflict-free booking within clinic hours (9–17, 30-min slots), next-open-slot suggestions, and regimen-based cadence inference.
  - `importer.py` — HMS/EMR **data integrator**: parses CSV/TSV, JSON arrays, and FHIR R4 Bundles into patients with flexible (aliased, case-insensitive) column matching; de-dupes by phone/MRN.
- `routes/` — thin HTTP layer (`auth`, `patients`, `followups`, `messages`, `dashboard`, `imports`). **Telegram inbound webhook is `POST /api/messages/telegram`** (handles the `/start <MRN>` linking flow). `imports` has `/preview` and `/patients` upload endpoints. `followups` also serves a token-based **iCalendar feed** (`GET /api/followups/calendar/{token}.ics`) so a doctor can subscribe to their appointments in Google Calendar. Proactive AI check-ins fire via `POST /api/messages/run-checkins` (doctor-triggered) and **`POST /api/messages/run-checkins/cron`** — an unauthenticated endpoint guarded by the `X-Cron-Key` header matching `CRON_SECRET`, called by the daily Render cron across all doctors.
- `seed.py` — synthetic, clinically-plausible oncology data. Tumour choice respects patient sex.

**Frontend** (`web/app/`, App Router, all pages are client components):
- `components/AppShell.tsx` wraps every page: client-side auth guard (redirects to `/login` when no token) + macOS-window chrome + `Sidebar`. `/login` renders outside the shell.
- `lib/api.ts` — typed fetch client; base URL from `NEXT_PUBLIC_API_BASE` (default `http://localhost:8000`).
- `lib/auth.ts` — token/user stored in localStorage; talks to the real `/api/auth` endpoints and holds the JWT used for authed calls.
- `lib/ui.tsx` — shared pills/avatars/time formatting; `components/icons.tsx` — inline SVG icon set.
- Pages mirror the sidebar (see `components/Sidebar.tsx`): dashboard (`page.tsx`), `patients/` (+ `[id]` detail), `appointments/`, `schedule/` (conflict-free booking), `messages/` (Telegram inbox), `oncology/{treatment,imaging,safety}`, `analytics/`, `integrator/` (data import UI), `login/`.

## Design

UI must match `ui_samples/Dashboard-UI.webp` — premium macOS look: grouped sidebar with a purple (`brand-500` = `#635bff`) active item, big greeting header, hero metric card with area chart, status banner, four stat cards, colored quick-action tiles. Inter font is loaded via CSS `@import` in `globals.css`, **not** `next/font` — the build environment has no network to Google Fonts.

## Constraints

- **Synthetic data only** — never commit real patient records.
- The **35% follow-up uplift** from the brief is a demo target, not clinically validated. It is labelled as such in the UI; keep it that way.
- The patient channel is **Telegram** (`TELEGRAM_BOT_TOKEN`); it stays in mock mode (logs instead of sends) until a bot token is set. The Meta WhatsApp client is retained but secondary. Sarvam (`SARVAM_API_KEY`) similarly falls back to templates when absent.
- `pip` on this machine's Python 3.14 can't build older pinned wheels; `requirements.txt` is intentionally loose and uses `psycopg` (v3) for Postgres and stdlib PBKDF2 + PyJWT (no `passlib`/`bcrypt`).
- Deploys as frontend-on-Vercel + backend-and-Postgres-on-Render via `render.yaml`; startup in `app/main.py` runs a lightweight idempotent migration and seeds the default login non-destructively.

## Note on README.md

`README.md` still describes the earlier **Twilio WhatsApp** channel in places; the code has since moved the patient channel to Telegram (plus a Meta WhatsApp client). Trust the code (`app/clients.py`, `routes/messages.py`) over the README when they disagree.
