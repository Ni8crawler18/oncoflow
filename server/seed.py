"""Initialize OncoFlow with a realistic demo panel.

Creates all tables, the clinician login (Dr. Kiran Rao), and a synthetic but
clinically-plausible panel of 10 oncology patients with follow-up history,
open symptoms and a little Telegram conversation — enough to make the
dashboard, Treatment Tracker, Imaging & Restaging and Analytics views come
alive for a demo.

Synthetic data only. Tumour choice respects patient sex.

Run:  python seed.py
"""
from datetime import datetime, timedelta, date, time

from app.database import Base, engine, SessionLocal
from app.models import User, Doctor, Patient, FollowUp, Symptom, Message
from app.security import hash_password

TODAY = datetime.now()


def _at(days_from_now: int, hour: int) -> datetime:
    """A clinic-hours datetime `days_from_now` (±) at the given hour."""
    d = (TODAY + timedelta(days=days_from_now)).date()
    return datetime.combine(d, time(hour, 0))


# Each patient: identity + a compact clinical profile. `cadence` is the
# follow-up interval in days; `cycles_done` past cycles are generated before
# today; `next_in` schedules the upcoming visit (None = needs scheduling,
# negative = overdue). `last_scan` is days since last restaging scan (None =
# never scanned → restaging due). `symptoms` are open post-care reports.
PANEL = [
    {
        "mrn": "ONC-1001", "name": "Lakshmi Narayanan", "phone": "+91 98840 11234",
        "age": 52, "sex": "Female", "cancer_type": "Breast cancer", "stage": "2-A",
        "line": "1st line", "regimen": "AC-T (doxorubicin/cyclophosphamide → paclitaxel)",
        "status": "On treatment", "risk": "medium", "dx_months": 4,
        "cadence": 21, "cycles_done": 3, "next_in": 9, "last_scan": 70, "symptoms": [],
    },
    {
        "mrn": "ONC-1002", "name": "Rajesh Kumar", "phone": "+91 99620 44518",
        "age": 61, "sex": "Male", "cancer_type": "Colorectal cancer", "stage": "3-B",
        "line": "1st line", "regimen": "FOLFOX", "status": "On treatment",
        "risk": "high", "dx_months": 5, "cadence": 14, "cycles_done": 6,
        "next_in": -3, "last_scan": 95,
        "symptoms": [("Tingling and numbness in fingertips, worse after infusions "
                      "(grade 2 peripheral neuropathy)", "moderate")],
    },
    {
        "mrn": "ONC-1003", "name": "Anjali Mehta", "phone": "+91 98190 77342",
        "age": 48, "sex": "Female", "cancer_type": "Ovarian cancer", "stage": "3-C",
        "line": "1st line", "regimen": "Carboplatin + Paclitaxel", "status": "On treatment",
        "risk": "high", "dx_months": 6, "cadence": 21, "cycles_done": 5,
        "next_in": 6, "last_scan": 44, "symptoms": [],
    },
    {
        "mrn": "ONC-1004", "name": "Mohammed Irfan", "phone": "+91 90030 55127",
        "age": 57, "sex": "Male", "cancer_type": "Non-Hodgkin lymphoma", "stage": "2",
        "line": "1st line", "regimen": "R-CHOP", "status": "On treatment",
        "risk": "medium", "dx_months": 3, "cadence": 21, "cycles_done": 2,
        "next_in": 12, "last_scan": None, "symptoms": [],
    },
    {
        "mrn": "ONC-1005", "name": "Sunita Deshpande", "phone": "+91 98230 66890",
        "age": 45, "sex": "Female", "cancer_type": "Cervical cancer", "stage": "2-B",
        "line": "1st line", "regimen": "Cisplatin (chemoradiation)", "status": "On treatment",
        "risk": "medium", "dx_months": 2, "cadence": 21, "cycles_done": 2,
        "next_in": None, "last_scan": 30, "symptoms": [],
    },
    {
        "mrn": "ONC-1006", "name": "Vikram Singh", "phone": "+91 98100 23471",
        "age": 64, "sex": "Male", "cancer_type": "Lung cancer (NSCLC)", "stage": "4",
        "line": "1st line", "regimen": "Pembrolizumab + Pemetrexed", "status": "On treatment",
        "risk": "high", "dx_months": 7, "cadence": 21, "cycles_done": 8,
        "next_in": 4, "last_scan": 100,
        "symptoms": [("Persistent dry cough with breathlessness on exertion over "
                      "the last few days", "severe")],
    },
    {
        "mrn": "ONC-1007", "name": "Priya Raghavan", "phone": "+91 94440 18806",
        "age": 34, "sex": "Female", "cancer_type": "Hodgkin lymphoma", "stage": "2-A",
        "line": "1st line", "regimen": "ABVD", "status": "On treatment",
        "risk": "low", "dx_months": 4, "cadence": 14, "cycles_done": 6,
        "next_in": 8, "last_scan": 55, "symptoms": [],
    },
    {
        "mrn": "ONC-1008", "name": "Arun Prasad", "phone": "+91 99400 73259",
        "age": 59, "sex": "Male", "cancer_type": "Pancreatic cancer", "stage": "3",
        "line": "1st line", "regimen": "FOLFIRINOX", "status": "On treatment",
        "risk": "high", "dx_months": 3, "cadence": 14, "cycles_done": 4,
        "next_in": -1, "last_scan": 60,
        "symptoms": [("Reduced appetite and mild nausea, eating less than usual",
                      "mild")],
    },
    {
        "mrn": "ONC-1009", "name": "Kavya Nair", "phone": "+91 96330 40715",
        "age": 41, "sex": "Female", "cancer_type": "Glioblastoma", "stage": "4",
        "line": "1st line", "regimen": "Temozolomide (Stupp protocol)",
        "status": "On treatment", "risk": "high", "dx_months": 3, "cadence": 28,
        "cycles_done": 2, "next_in": 15, "last_scan": 85,
        "symptoms": [("Morning headaches with occasional nausea", "moderate")],
    },
    {
        "mrn": "ONC-1010", "name": "Suresh Babu", "phone": "+91 98860 91234",
        "age": 68, "sex": "Male", "cancer_type": "Prostate cancer", "stage": "3",
        "line": "1st line", "regimen": "ADT (androgen deprivation therapy)",
        "status": "Surveillance", "risk": "low", "dx_months": 9, "cadence": 90,
        "cycles_done": 2, "next_in": 25, "last_scan": 120, "symptoms": [],
    },
]

CYCLE_ROTATION = ["labs", "chemo", "review"]
KIND_TITLE = {
    "labs": "Pre-cycle labs & review",
    "chemo": "Chemotherapy cycle",
    "review": "Clinical review",
    "imaging": "Restaging scan",
}


def build_followups(p: dict, patient_id: int, hour: int) -> tuple[list[FollowUp], date]:
    """Generate past (completed) cycles, an optional restaging scan, and the
    next scheduled visit for one patient. Returns (followups, last_contact)."""
    fus: list[FollowUp] = []
    cadence = p["cadence"]
    last_contact = None

    # Past completed cycles, spaced by cadence and ending before today.
    for i in range(p["cycles_done"]):
        back = (p["cycles_done"] - i) * cadence
        kind = CYCLE_ROTATION[i % len(CYCLE_ROTATION)]
        when = _at(-back, hour)
        fus.append(FollowUp(
            patient_id=patient_id, kind=kind, title=KIND_TITLE[kind],
            scheduled_for=when, duration_min=60 if kind == "chemo" else 30,
            status="completed", priority="normal",
            reason=f"Routine {kind} on the {p['regimen']} course.",
        ))
        last_contact = when.date()

    # A completed restaging scan in the past (drives Imaging & Restaging).
    if p["last_scan"] is not None:
        when = _at(-p["last_scan"], hour)
        fus.append(FollowUp(
            patient_id=patient_id, kind="imaging", title="Restaging CT scan",
            scheduled_for=when, duration_min=30, status="completed",
            priority="normal", reason="Scheduled restaging to assess response.",
        ))

    # Upcoming visit (or an overdue one if next_in is negative).
    if p["next_in"] is not None:
        kind = CYCLE_ROTATION[p["cycles_done"] % len(CYCLE_ROTATION)]
        when = _at(p["next_in"], hour)
        overdue = p["next_in"] < 0
        fus.append(FollowUp(
            patient_id=patient_id, kind=kind, title=KIND_TITLE[kind],
            scheduled_for=when, duration_min=60 if kind == "chemo" else 30,
            status="scheduled",
            priority="high" if p["risk"] == "high" else "normal",
            reason=(f"Overdue — expected {abs(p['next_in'])} day(s) ago; needs "
                    f"re-engagement." if overdue
                    else f"Next {kind} on the {cadence}-day {p['regimen']} cadence."),
        ))

    return fus, last_contact


def run():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    db.add(User(
        name="Dr. Kiran Rao", email="kiran@oncoflow.health",
        password_hash=hash_password("oncoflow"), specialty="Medical Oncology",
    ))
    doctor = Doctor(name="Dr. Kiran Rao", email="kiran@oncoflow.health",
                    specialty="Medical Oncology")
    db.add(doctor)
    db.flush()

    for idx, p in enumerate(PANEL):
        hour = 9 + (idx % 7)  # stagger across clinic hours to avoid overlaps
        patient = Patient(
            mrn=p["mrn"], name=p["name"], phone=p["phone"], age=p["age"],
            sex=p["sex"], cancer_type=p["cancer_type"], stage=p["stage"],
            treatment_line=p["line"], regimen=p["regimen"], status=p["status"],
            risk=p["risk"],
            diagnosed_on=(TODAY - timedelta(days=p["dx_months"] * 30)).date(),
            doctor_id=doctor.id,
        )
        db.add(patient)
        db.flush()

        fus, last_contact = build_followups(p, patient.id, hour)
        for fu in fus:
            db.add(fu)

        for desc, severity in p["symptoms"]:
            reported = TODAY - timedelta(days=2)
            db.add(Symptom(
                patient_id=patient.id, description=desc, severity=severity,
                source="telegram", status="open", reported_at=reported,
            ))
            # A matching inbound report + AI acknowledgement, for the timeline.
            db.add(Message(
                patient_id=patient.id, direction="inbound", channel="telegram",
                body=desc, category="symptom", created_at=reported,
            ))
            db.add(Message(
                patient_id=patient.id, direction="outbound", channel="telegram",
                body=("Thanks for letting us know. When did this start, and how "
                      "severe does it feel on a scale of 1 to 10?"),
                category="general", created_at=reported + timedelta(minutes=3),
            ))

        patient.last_contact = last_contact

    db.commit()
    n = db.query(Patient).count()
    db.close()
    print(f"Seeded OncoFlow: {n} patients, login kiran@oncoflow.health / oncoflow")


if __name__ == "__main__":
    run()
