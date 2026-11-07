"""Data integrator: parse patient records from multiple formats into the DB.

Supported inputs:
  - CSV / TSV  (header row with column names)
  - JSON array of patient objects
  - FHIR R4 Bundle, JSON *or* XML (extracts Patient + linked Condition and
    MedicationStatement/MedicationRequest resources, best-effort)

Column / field names are matched flexibly (case-insensitive, common aliases),
so records exported from different HMS / EMR systems can be ingested without
hand-editing. Rows are de-duplicated against existing patients by phone or MRN.
"""
from __future__ import annotations

import csv
import io
import json
import xml.etree.ElementTree as ET
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


def _age_from_birthdate(bd: str) -> int | None:
    for fmt in ("%Y-%m-%d", "%Y"):
        try:
            born = datetime.strptime(bd[: len(fmt) + 2 if fmt == "%Y-%m-%d" else 4], fmt)
            today = date.today()
            return today.year - born.year - (
                (today.month, today.day) < (born.month, born.day))
        except ValueError:
            continue
    return None


def _codeable_text(cc: dict) -> str:
    """Best text for a FHIR CodeableConcept (JSON): text, else first coding."""
    if not cc:
        return ""
    if cc.get("text"):
        return cc["text"]
    for c in cc.get("coding", []):
        if c.get("display"):
            return c["display"]
    return ""


def _ref_id(ref: str) -> str:
    """Normalize a subject reference (Patient/p1, urn:uuid:..) to a bare key."""
    if not ref:
        return ""
    return ref.split("/")[-1].replace("urn:uuid:", "")


def _rows_from_fhir_bundle(bundle: dict) -> list[dict]:
    """Extract patients from a JSON FHIR Bundle, enriching each with the
    Condition (diagnosis/stage/onset) and medication that reference them."""
    patients: dict[str, dict] = {}
    conditions: list[dict] = []
    meds: list[dict] = []

    for entry in bundle.get("entry", []):
        res = entry.get("resource", {})
        rtype = res.get("resourceType")
        key = res.get("id") or _ref_id(entry.get("fullUrl", ""))
        if rtype == "Patient":
            n = (res.get("name") or [{}])[0]
            name = " ".join(n.get("given", []) + [n.get("family", "")]).strip()
            phone = next((t.get("value", "") for t in res.get("telecom", [])
                          if t.get("system") == "phone"), "")
            mrn = next((i.get("value") for i in (res.get("identifier") or [])
                        if i.get("value")), res.get("id", ""))
            row = {"name": name, "sex": res.get("gender", ""), "phone": phone,
                   "mrn": mrn}
            age = _age_from_birthdate(res.get("birthDate", ""))
            if age is not None:
                row["age"] = age
            patients[key] = row
        elif rtype == "Condition":
            conditions.append(res)
        elif rtype in ("MedicationStatement", "MedicationRequest"):
            meds.append(res)

    for c in conditions:
        pid = _ref_id((c.get("subject") or {}).get("reference", ""))
        p = patients.get(pid)
        if not p:
            continue
        p.setdefault("cancer_type", _codeable_text(c.get("code", {})))
        stages = c.get("stage") or []
        if stages and not p.get("stage"):
            p["stage"] = _codeable_text(stages[0].get("summary", {}))
        if c.get("onsetDateTime") and not p.get("diagnosed_on"):
            p["diagnosed_on"] = c["onsetDateTime"][:10]

    for m in meds:
        pid = _ref_id((m.get("subject") or {}).get("reference", ""))
        p = patients.get(pid)
        if p and not p.get("regimen"):
            p["regimen"] = _codeable_text(m.get("medicationCodeableConcept", {}))

    return list(patients.values())


# ---- FHIR XML ----
FHIR_NS = "{http://hl7.org/fhir}"


def _lv(elem, *path) -> str:
    """Navigate child elements by local tag name and return the `value`
    attribute of the final node (FHIR XML stores scalars as value=...)."""
    cur = elem
    for tag in path:
        if cur is None:
            return ""
        cur = cur.find(f"{FHIR_NS}{tag}")
    return (cur.get("value") if cur is not None else "") or ""


def _rows_from_fhir_xml(text: str) -> list[dict]:
    root = ET.fromstring(text)
    patients: dict[str, dict] = {}
    conditions, meds = [], []

    for entry in root.findall(f"{FHIR_NS}entry"):
        res_wrap = entry.find(f"{FHIR_NS}resource")
        if res_wrap is None:
            continue
        res = list(res_wrap)[0] if len(res_wrap) else None
        if res is None:
            continue
        rtype = res.tag.replace(FHIR_NS, "")
        key = _lv(res, "id") or _ref_id(_lv(entry, "fullUrl"))
        if rtype == "Patient":
            name_el = res.find(f"{FHIR_NS}name")
            given = [g.get("value", "") for g in name_el.findall(f"{FHIR_NS}given")] \
                if name_el is not None else []
            family = _lv(name_el, "family") if name_el is not None else ""
            name = " ".join([*given, family]).strip()
            phone = ""
            for tel in res.findall(f"{FHIR_NS}telecom"):
                if _lv(tel, "system") == "phone":
                    phone = _lv(tel, "value")
                    break
            ident = res.find(f"{FHIR_NS}identifier")
            mrn = (_lv(ident, "value") if ident is not None else "") or _lv(res, "id")
            row = {"name": name, "sex": _lv(res, "gender"), "phone": phone,
                   "mrn": mrn}
            age = _age_from_birthdate(_lv(res, "birthDate"))
            if age is not None:
                row["age"] = age
            patients[key] = row
        elif rtype == "Condition":
            conditions.append(res)
        elif rtype in ("MedicationStatement", "MedicationRequest"):
            meds.append(res)

    def _cc_text(parent, tag) -> str:
        cc = parent.find(f"{FHIR_NS}{tag}")
        if cc is None:
            return ""
        t = _lv(cc, "text")
        if t:
            return t
        coding = cc.find(f"{FHIR_NS}coding")
        return _lv(coding, "display") if coding is not None else ""

    for c in conditions:
        subj = c.find(f"{FHIR_NS}subject")
        pid = _ref_id(_lv(subj, "reference")) if subj is not None else ""
        p = patients.get(pid)
        if not p:
            continue
        p.setdefault("cancer_type", _cc_text(c, "code"))
        stage = c.find(f"{FHIR_NS}stage")
        if stage is not None and not p.get("stage"):
            p["stage"] = _cc_text(stage, "summary")
        onset = _lv(c, "onsetDateTime")
        if onset and not p.get("diagnosed_on"):
            p["diagnosed_on"] = onset[:10]

    for m in meds:
        subj = m.find(f"{FHIR_NS}subject")
        pid = _ref_id(_lv(subj, "reference")) if subj is not None else ""
        p = patients.get(pid)
        if p and not p.get("regimen"):
            p["regimen"] = _cc_text(m, "medicationCodeableConcept")

    return list(patients.values())


def parse(filename: str, content: bytes) -> list[dict]:
    """Return a list of normalized patient dicts (canonical keys)."""
    text = content.decode("utf-8-sig", errors="replace")
    name = filename.lower()
    stripped = text.lstrip()

    if name.endswith((".ttl", ".rdf")) or stripped.startswith("@prefix"):
        raise ValueError(
            "FHIR Turtle/RDF is not supported yet — please supply the "
            "bundle as FHIR XML or JSON.")

    if name.endswith(".xml") or stripped.startswith("<"):
        raw_rows = _rows_from_fhir_xml(text)
        mapping = None  # already canonical
        normalized = []
        for raw in raw_rows:
            rec = {f: _coerce(f, raw[f]) for f in ALIASES if f in raw}
            normalized.append(rec)
        return normalized

    if name.endswith(".json") or stripped.startswith(("{", "[")):
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
