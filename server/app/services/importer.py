"""Data integrator: parse patient records from multiple formats into the DB.

Supported inputs:
  - CSV / TSV  (header row with column names)
  - JSON array of patient objects
  - FHIR R4 Bundle JSON (extracts Patient resources, best-effort)

Column / field names are matched flexibly (case-insensitive, common aliases),
so records exported from different HMS / EMR systems can be ingested without
hand-editing. Rows are de-duplicated against existing patients by phone or MRN.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Patient

# Canonical field -> accepted aliases (lowercased, stripped of non-alphanumerics)
ALIASES = {
    "name": ["name", "patientname", "fullname", "patient"],
    "phone": ["phone", "mobile", "contact", "phonenumber", "whatsapp", "cell"],
    "age": ["age"],
    "sex": ["sex", "gender"],
    "cancer_type": ["cancertype", "diagnosis", "dx", "primarydiagnosis", "tumour", "tumor", "condition"],
    "stage": ["stage", "tnmstage"],
    "treatment_line": ["treatmentline", "line"],
    "regimen": ["regimen", "protocol", "chemo", "treatment"],
    "status": ["status"],
    "risk": ["risk", "risklevel"],
    "mrn": ["mrn", "medicalrecordnumber", "recordno", "id", "patientid"],
    "diagnosed_on": ["diagnosedon", "diagnosisdate", "dxdate", "diagnosed"],
}


def _norm_key(k: str) -> str:
    return "".join(ch for ch in k.lower() if ch.isalnum())


def _build_lookup(headers: list[str]) -> dict[str, str]:
    """Map a source header -> canonical field name."""
    alias_to_field = {}
    for field, aliases in ALIASES.items():
        for a in aliases:
            alias_to_field[a] = field
    mapping = {}
    for h in headers:
        canon = alias_to_field.get(_norm_key(h))
        if canon:
            mapping[h] = canon
    return mapping


def _coerce(field: str, value):
    if value is None:
        return None
    value = str(value).strip()
    if value == "":
        return None
    if field == "age":
        try:
            return int(float(value))
        except ValueError:
            return None
    if field == "sex":
        v = value.lower()
        if v in ("m", "male"):
            return "Male"
        if v in ("f", "female"):
            return "Female"
        return value.title()
    if field == "risk":
        v = value.lower()
        return v if v in ("low", "medium", "high") else "medium"
    if field == "diagnosed_on":
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        return None
    return value


def _rows_from_csv(text: str) -> list[dict]:
    sniff_delim = "\t" if text.count("\t") > text.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=sniff_delim)
    return [dict(r) for r in reader]


def _rows_from_fhir_bundle(bundle: dict) -> list[dict]:
    rows = []
    for entry in bundle.get("entry", []):
        res = entry.get("resource", {})
        if res.get("resourceType") != "Patient":
            continue
        name = ""
        if res.get("name"):
            n = res["name"][0]
            name = " ".join(n.get("given", []) + [n.get("family", "")]).strip()
        phone = ""
        for t in res.get("telecom", []):
            if t.get("system") == "phone":
                phone = t.get("value", "")
                break
        rows.append({
            "name": name,
            "sex": res.get("gender", ""),
            "phone": phone,
            "mrn": res.get("id", ""),
        })
    return rows


def parse(filename: str, content: bytes) -> list[dict]:
    """Return a list of normalized patient dicts (canonical keys)."""
    text = content.decode("utf-8-sig", errors="replace")
    name = filename.lower()

    if name.endswith(".json") or text.lstrip().startswith(("{", "[")):
        data = json.loads(text)
        if isinstance(data, dict) and data.get("resourceType") == "Bundle":
            raw_rows = _rows_from_fhir_bundle(data)
            mapping = None  # already canonical
        elif isinstance(data, list):
            raw_rows = data
            mapping = _build_lookup(list(raw_rows[0].keys())) if raw_rows else {}
        elif isinstance(data, dict):
            raw_rows = [data]
            mapping = _build_lookup(list(data.keys()))
        else:
            raise ValueError("Unrecognized JSON structure")
    else:
        raw_rows = _rows_from_csv(text)
        mapping = _build_lookup(list(raw_rows[0].keys())) if raw_rows else {}

    normalized = []
    for raw in raw_rows:
        rec: dict = {}
        if mapping is None:
            src = raw  # canonical keys already
        else:
            src = {}
            for k, v in raw.items():
                field = mapping.get(k)
                if field:
                    src[field] = v
        for field in ALIASES:
            if field in src:
                rec[field] = _coerce(field, src[field])
        normalized.append(rec)
    return normalized


def import_patients(db: Session, rows: list[dict], doctor_id: int = 1) -> dict:
    """Insert normalized rows as patients. Returns a summary."""
    existing = db.scalars(select(Patient)).all()
    by_phone = {p.phone for p in existing if p.phone}
    by_mrn = {p.mrn for p in existing if p.mrn}
    next_mrn = 1001 + len(existing)

    imported, skipped, errors = 0, 0, []
    for i, rec in enumerate(rows, start=1):
        name = rec.get("name")
        if not name:
            errors.append(f"Row {i}: missing name")
            continue
        phone = rec.get("phone") or ""
        mrn = rec.get("mrn")
        if (phone and phone in by_phone) or (mrn and mrn in by_mrn):
            skipped += 1
            continue
        if not mrn:
            mrn = f"ONC-{next_mrn}"
            next_mrn += 1

        patient = Patient(
            mrn=mrn,
            name=name,
            phone=phone,
            age=rec.get("age") or 0,
            sex=rec.get("sex") or "Unknown",
            cancer_type=rec.get("cancer_type") or "Unspecified",
            stage=rec.get("stage") or "-",
            treatment_line=rec.get("treatment_line") or "1st line",
            regimen=rec.get("regimen") or "",
            status=rec.get("status") or "On treatment",
            risk=rec.get("risk") or "medium",
            diagnosed_on=rec.get("diagnosed_on") or date.today(),
            last_contact=None,
            doctor_id=doctor_id,
        )
        db.add(patient)
        by_phone.add(phone)
        by_mrn.add(mrn)
        imported += 1

    db.commit()
    return {"imported": imported, "skipped": skipped, "errors": errors,
            "total": len(rows)}
