# OncoFlow — Build Summary

A doctor-facing oncology follow-up portal: a clinician manages long-term cancer
patients, patients report symptoms over a chat channel, an AI assistant follows
up and captures symptoms, and appointments are scheduled conflict-free on a
calendar. Built as a real, deployable product (no mock data).

## Live

- **Frontend (Vercel):** https://oncoflow-health.vercel.app
- **Backend API (Render):** https://oncoflow-api-5kxd.onrender.com
- **Patient bot (Telegram):** [@oncoflow_bot](https://t.me/oncoflow_bot)
- **Login:** `kiran@oncoflow.health` / `oncoflow` (Dr. Kiran Rao)

> Render's free tier sleeps when idle; the first request after a quiet spell
> takes a few seconds to wake.

## Stack

- **Backend:** FastAPI + SQLAlchemy 2.x, PostgreSQL (Render, Singapore),
  psycopg v3, pydantic-settings.
- **Frontend:** Next.js 14 (App Router) + Tailwind, Inter via CSS import,
  brand purple `#635bff`, premium macOS-style UI matching the design samples.
- **AI:** Sarvam (`sarvam-105b-conversations`) for patient chat, check-ins, and
  symptom triage/extraction.
- **Patient channel:** Telegram Bot API (webhook-driven).
- **Auth:** real register/login — PBKDF2 password hashing, PyJWT tokens, users
  table; non-destructive startup seed of the Kiran login.

## What's implemented

### Doctor portal
- Dashboard with live stats, activity, and follow-up trend.
- Patient panel + patient detail (Timeline, Post-care Symptoms, Follow-ups,
  Telegram, Notes tabs).
- Add Patient flow that provisions a patient and surfaces their linking QR +
  deep link.
- Appointments calendar (conflict-free).
- Data integrator: import patients from CSV / TSV / JSON / FHIR with flexible
  column aliasing and dedup.
- Real Postgres persistence throughout; no mock/demo data.

### Patient channel (Telegram)
- Patients link by scanning a **QR code** or opening a per-patient deep link
  `t.me/oncoflow_bot?start=<MRN>` and tapping Start — no manual ID typing.
- QR shown both at registration (Add Patient modal) and on the patient's
  Telegram tab while unlinked.
- On first link, the **care team speaks first**: an automatic personalized AI
  check-in is sent (within Telegram's rule that a bot can't message a user
  before that user starts it).
- Inbound symptom messages are AI-triaged, summarized, graded
  (mild/moderate/severe), and filed under the patient's Post-care Symptoms.
- AI generates contextual follow-up replies using patient history.

### Scheduling
- Deterministic auto-scheduling: cadence inferred from the patient's own
  appointment history (median gap), else regimen-based cadence.
- Conflict-free slot finder within clinic hours, skips weekends.
- **Scheduling by chat:** when a patient asks to book over Telegram, the bot
  parses a preferred day ("next monday", "tomorrow", a weekday, "next week"),
  books a real conflict-free appointment on the doctor's calendar, and confirms
  with the concrete date/time signed *on behalf of Dr. Kiran Rao*.

## Test flow

1. Log in at the Vercel URL as Dr. Kiran Rao.
2. Add a patient (e.g. Venkatesh R) — the modal shows their QR + deep link.
3. Patient scans the QR / opens the bot and taps Start → auto-linked, and the
   care-team check-in arrives automatically.
4. Patient messages symptoms → captured under Post-care Symptoms with severity;
   AI replies.
5. Patient asks to schedule → appointment is booked and appears on the
   Appointments calendar with a confirmation naming the doctor and time.

## Channel notes / decisions

- **Telegram** is the patient channel. A bot cannot initiate contact before the
  user starts it (Telegram anti-spam rule), so linking needs one Start tap —
  made effortless via QR, and the clinic's first real message is auto-sent on
  link.
- **Twilio WhatsApp** was dropped: the sandbox requires a `join <code>`
  handshake with a 24h messaging window and no API to set its webhook, and
  production messaging-first needs Meta Business verification (the business was
  flagged as restricted). WhatsApp therefore can't message-first any more easily
  than Telegram; only SMS can, which was considered but not adopted.

## Repo layout

- `server/` — FastAPI app (`app/routes`, `app/services`, `app/models.py`,
  `app/clients.py`), `seed.py`, `requirements.txt`, `render.yaml`.
- `web/` — Next.js app (`app/`, `components/`, `lib/`).
- `CLAUDE.md` — project guidance for future work.
