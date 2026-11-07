"""Initialize OncoFlow with a clean database.

Creates all tables and a single clinician login (Dr. Kiran Rao). No patient,
message, follow-up or symptom data is seeded - the portal starts empty and is
populated by onboarding real patients (manually or via the Data Integrator).

Run:  python seed.py
"""
from app.database import Base, engine, SessionLocal
from app.models import User, Doctor
from app.security import hash_password


def run():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    db.add(User(
        name="Dr. Kiran Rao",
        email="kiran@oncoflow.health",
        password_hash=hash_password("oncoflow"),
        specialty="Medical Oncology",
    ))
    db.add(Doctor(
        name="Dr. Kiran Rao",
        email="kiran@oncoflow.health",
        specialty="Medical Oncology",
    ))
    db.commit()
    db.close()
    print("Initialized OncoFlow: clean database with login kiran@oncoflow.health / oncoflow")


if __name__ == "__main__":
    run()
