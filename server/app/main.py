from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from . import models  # noqa: F401  (register models)
from .clients import telegram
from .routes import patients, followups, messages, dashboard, auth, imports

app = FastAPI(title=f"{settings.app_name} API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_origin_regex=r"https://.*\.vercel\.app",  # Vercel preview deployments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    # Lightweight migration: add telegram_chat_id if an older patients table
    # predates it (Postgres + SQLite both support IF NOT EXISTS).
    from sqlalchemy import text
    try:
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE patients ADD COLUMN IF NOT EXISTS telegram_chat_id VARCHAR(32)"
            ))
            conn.execute(text(
                "ALTER TABLE followups ADD COLUMN IF NOT EXISTS reason TEXT DEFAULT ''"
            ))
    except Exception:
        pass
    # Ensure the default clinician login exists (non-destructive; only creates
    # it when there are no users yet). Never wipes existing data.
    from sqlalchemy import select
    from .database import SessionLocal
    from .models import User, Doctor
    from .security import hash_password

    db = SessionLocal()
    try:
        if db.scalar(select(User).limit(1)) is None:
            db.add(User(name="Dr. Kiran Rao", email="kiran@oncoflow.health",
                        password_hash=hash_password("oncoflow"),
                        specialty="Medical Oncology"))
            if db.scalar(select(Doctor).limit(1)) is None:
                db.add(Doctor(name="Dr. Kiran Rao", email="kiran@oncoflow.health",
                              specialty="Medical Oncology"))
            db.commit()
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name, "telegram_live": telegram.live}


app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(followups.router)
app.include_router(messages.router)
app.include_router(dashboard.router)
app.include_router(imports.router)
