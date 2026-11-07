"""SQLAlchemy ORM models for OncoFlow."""
from datetime import datetime, date
from sqlalchemy import String, Integer, Text, Date, DateTime, ForeignKey, Float, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    specialty: Mapped[str] = mapped_column(String(120), default="Medical Oncology")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True)
    specialty: Mapped[str] = mapped_column(String(120), default="Medical Oncology")

    patients: Mapped[list["Patient"]] = relationship(back_populates="doctor")


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    mrn: Mapped[str] = mapped_column(String(32), unique=True)  # medical record no.
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(32))  # E.164, used for WhatsApp
    age: Mapped[int] = mapped_column(Integer)
    sex: Mapped[str] = mapped_column(String(16))

    # Oncology-specific
    cancer_type: Mapped[str] = mapped_column(String(120))
    stage: Mapped[str] = mapped_column(String(16))
    treatment_line: Mapped[str] = mapped_column(String(80), default="1st line")
    regimen: Mapped[str] = mapped_column(String(160), default="")
    status: Mapped[str] = mapped_column(String(32), default="On treatment")
    risk: Mapped[str] = mapped_column(String(16), default="medium")  # low|medium|high

    diagnosed_on: Mapped[date] = mapped_column(Date)
    last_contact: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Telegram chat id, set when the patient links via the bot.
    telegram_chat_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)

    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"))
    doctor: Mapped["Doctor"] = relationship(back_populates="patients")

    followups: Mapped[list["FollowUp"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    messages: Mapped[list["Message"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    notes: Mapped[list["Note"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    symptoms: Mapped[list["Symptom"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )


class FollowUp(Base):
    __tablename__ = "followups"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    kind: Mapped[str] = mapped_column(String(48))  # review|chemo|imaging|labs|consult
    title: Mapped[str] = mapped_column(String(200))
    scheduled_for: Mapped[datetime] = mapped_column(DateTime)
    duration_min: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(24), default="scheduled")  # scheduled|completed|missed|overdue
    priority: Mapped[str] = mapped_column(String(16), default="normal")  # low|normal|high
    # Why this appointment exists — the clinical rationale shown to the doctor
    # and used in the patient's Telegram notification.
    reason: Mapped[str] = mapped_column(Text, default="")

    patient: Mapped["Patient"] = relationship(back_populates="followups")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    direction: Mapped[str] = mapped_column(String(12))  # inbound|outbound
    channel: Mapped[str] = mapped_column(String(16), default="whatsapp")
    body: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(32), default="general")  # symptom|feedback|general
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    patient: Mapped["Patient"] = relationship(back_populates="messages")


class Symptom(Base):
    """Post-care symptom reported by a patient (via WhatsApp)."""
    __tablename__ = "symptoms"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(16), default="unknown")  # mild|moderate|severe|unknown
    source: Mapped[str] = mapped_column(String(24), default="whatsapp")
    status: Mapped[str] = mapped_column(String(16), default="open")  # open|reviewed
    reported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    patient: Mapped["Patient"] = relationship(back_populates="symptoms")


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    author: Mapped[str] = mapped_column(String(120), default="Care team")
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    patient: Mapped["Patient"] = relationship(back_populates="notes")
