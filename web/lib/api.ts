export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json();
}

export interface Patient {
  id: number;
  mrn: string;
  name: string;
  phone: string;
  age: number;
  sex: string;
  cancer_type: string;
  stage: string;
  treatment_line: string;
  regimen: string;
  status: string;
  risk: "low" | "medium" | "high";
  diagnosed_on: string;
  last_contact: string | null;
  doctor_id: number;
}

export interface FollowUp {
  id: number;
  patient_id: number;
  kind: string;
  title: string;
  scheduled_for: string;
  duration_min: number;
  status: string;
  priority: string;
  patient_name?: string;
  cancer_type?: string;
}

export interface Message {
  id: number;
  patient_id: number;
  direction: "inbound" | "outbound";
  channel: string;
  body: string;
  category: "symptom" | "feedback" | "general";
  created_at: string;
}

export interface Note {
  id: number;
  patient_id: number;
  author: string;
  body: string;
  created_at: string;
}

export interface Symptom {
  id: number;
  patient_id: number;
  description: string;
  severity: string;
  source: string;
  status: string;
  reported_at: string;
}

export interface SymptomFeed extends Symptom {
  patient_name: string;
  cancer_type: string;
  regimen: string;
}

export interface Stats {
  total_patients: number;
  high_risk: number;
  overdue: number;
  due_today: number;
  new_symptoms: number;
  adherence: number;
  followup_uplift_pct: number;
}

export interface Activity {
  patient_id: number;
  patient_name: string;
  body: string;
  category: string;
  direction: string;
  created_at: string;
}

export const api = {
  stats: () => req<Stats>("/api/dashboard/stats"),
  activity: () => req<Activity[]>("/api/dashboard/activity"),
  trend: () => req<{ month: string; completed: number }[]>("/api/dashboard/trend"),
  patients: (q = "") =>
    req<Patient[]>(`/api/patients${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  patient: (id: number) => req<Patient>(`/api/patients/${id}`),
  patientMessages: (id: number) => req<Message[]>(`/api/patients/${id}/messages`),
  patientFollowups: (id: number) => req<FollowUp[]>(`/api/patients/${id}/followups`),
  patientNotes: (id: number) => req<Note[]>(`/api/patients/${id}/notes`),
  patientSymptoms: (id: number) => req<Symptom[]>(`/api/patients/${id}/symptoms`),
  aiCheckin: (patient_id: number) =>
    req<Message>("/api/messages/checkin", {
      method: "POST",
      body: JSON.stringify({ patient_id }),
    }),
  symptomsFeed: () => req<SymptomFeed[]>("/api/dashboard/symptoms"),
  addNote: (id: number, body: string) =>
    req<Note>(`/api/patients/${id}/notes`, {
      method: "POST",
      body: JSON.stringify({ patient_id: id, body }),
    }),
  followups: (status = "scheduled") =>
    req<FollowUp[]>(`/api/followups?status=${status}`),
  allFollowups: () => req<FollowUp[]>(`/api/followups`),
  autoSchedule: () =>
    req<{ created: number; already_scheduled: number }>(
      "/api/followups/auto-schedule",
      { method: "POST" }
    ),
  createPatient: (payload: {
    name: string;
    phone: string;
    age: number;
    sex: string;
    cancer_type: string;
    stage: string;
    treatment_line?: string;
    regimen?: string;
    risk?: string;
  }) =>
    req<Patient>("/api/patients", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  slots: (day: string) =>
    req<{ day: string; slots: string[] }>(`/api/followups/slots?day=${day}`),
  createFollowup: (payload: {
    patient_id: number;
    kind: string;
    title: string;
    scheduled_for: string;
    duration_min: number;
    priority?: string;
  }) =>
    req<FollowUp>("/api/followups", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  messages: (category = "") =>
    req<Message[]>(`/api/messages${category ? `?category=${category}` : ""}`),
  sendMessage: (patient_id: number, body: string) =>
    req<Message>("/api/messages/send", {
      method: "POST",
      body: JSON.stringify({ patient_id, body }),
    }),
  importPreview: (file: File) => uploadFile<ImportPreview>("/api/import/preview", file),
  importPatients: (file: File) => uploadFile<ImportResult>("/api/import/patients", file),
};

export interface ImportPreview {
  filename: string;
  count: number;
  rows: Record<string, any>[];
}

export interface ImportResult {
  imported: number;
  skipped: number;
  errors: string[];
  total: number;
}

async function uploadFile<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}${path}`, { method: "POST", body: form });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((data as any)?.detail || `${res.status}`);
  return data as T;
}
