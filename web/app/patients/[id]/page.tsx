"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Icon } from "@/components/icons";
import { Avatar, riskPill, statusPill, categoryPill, formatTime, timeAgo } from "@/lib/ui";
import { api, Patient, Message, FollowUp, Note, Symptom } from "@/lib/api";

const SEV_COLOR: Record<string, string> = {
  severe: "bg-rose-50 text-rose-600",
  moderate: "bg-amber-50 text-amber-600",
  mild: "bg-emerald-50 text-emerald-600",
  unknown: "bg-gray-100 text-gray-500",
};

export default function PatientDetail() {
  const { id } = useParams<{ id: string }>();
  const pid = Number(id);
  const [patient, setPatient] = useState<Patient | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [followups, setFollowups] = useState<FollowUp[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [symptoms, setSymptoms] = useState<Symptom[]>([]);
  const [tab, setTab] = useState<
    "timeline" | "symptoms" | "followups" | "messages" | "notes"
  >("timeline");
  const [reply, setReply] = useState("");
  const [note, setNote] = useState("");
  const [chatErr, setChatErr] = useState("");
  const [busy, setBusy] = useState(false);

  function load() {
    api.patient(pid).then(setPatient).catch(() => {});
    api.patientMessages(pid).then(setMessages).catch(() => {});
    api.patientFollowups(pid).then(setFollowups).catch(() => {});
    api.patientNotes(pid).then(setNotes).catch(() => {});
    api.patientSymptoms(pid).then(setSymptoms).catch(() => {});
  }
  useEffect(load, [pid]);

  async function sendReply() {
    if (!reply.trim()) return;
    setChatErr("");
    try {
      await api.sendMessage(pid, reply);
      setReply("");
      api.patientMessages(pid).then(setMessages);
    } catch (e: any) {
      setChatErr(e.message || "Could not send");
    }
  }
  async function aiCheckin() {
    setBusy(true);
    setChatErr("");
    try {
      await api.aiCheckin(pid);
      api.patientMessages(pid).then(setMessages);
    } catch (e: any) {
      setChatErr(e.message || "Could not send check-in");
    } finally {
      setBusy(false);
    }
  }
  async function addNote() {
    if (!note.trim()) return;
    await api.addNote(pid, note);
    setNote("");
    api.patientNotes(pid).then(setNotes);
  }

  if (!patient) return <div className="text-ink-400">Loading…</div>;

  const facts = [
    ["Diagnosis", patient.cancer_type],
    ["Stage", patient.stage],
    ["Treatment line", patient.treatment_line],
    ["Regimen", patient.regimen],
    ["Diagnosed", patient.diagnosed_on],
    ["Last contact", patient.last_contact ?? "-"],
    ["Phone (WhatsApp)", patient.phone],
    ["MRN", patient.mrn],
  ];

  const tabs = [
    ["timeline", "Timeline"],
    ["symptoms", `Post-care Symptoms (${symptoms.length})`],
    ["followups", `Follow-ups (${followups.length})`],
    ["messages", `WhatsApp (${messages.length})`],
    ["notes", `Notes (${notes.length})`],
  ] as const;

  return (
    <div>
      <Link href="/patients" className="mb-4 inline-flex items-center gap-1 text-sm text-ink-500 hover:text-ink-900">
        ← Back to patients
      </Link>

      <div className="card mb-5 p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <Avatar name={patient.name} />
            <div>
              <h1 className="text-2xl font-bold text-ink-900">{patient.name}</h1>
              <p className="text-sm text-ink-500">
                {patient.age} yrs · {patient.sex} · {patient.status}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {riskPill(patient.risk)}
          </div>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-x-8 gap-y-3 sm:grid-cols-4">
          {facts.map(([k, v]) => (
            <div key={k}>
              <div className="text-[11px] uppercase tracking-wider text-ink-400">{k}</div>
              <div className="mt-0.5 text-sm font-medium text-ink-800">{v}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="mb-4 flex gap-1 rounded-xl bg-white p-1 shadow-soft">
        {tabs.map(([t, label]) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
              tab === t ? "bg-brand-500 text-white" : "text-ink-500 hover:bg-black/5"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "timeline" && (
        <div className="card p-5">
          <div className="space-y-4">
            {[...followups]
              .sort((a, b) => b.scheduled_for.localeCompare(a.scheduled_for))
              .map((f) => (
                <div key={`f${f.id}`} className="flex gap-3">
                  <div className="mt-1 flex h-8 w-8 items-center justify-center rounded-full bg-brand-50 text-brand-600">
                    <Icon.calendar width={15} height={15} />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-ink-900">{f.title}</span>
                      {statusPill(f.status)}
                    </div>
                    <div className="text-xs text-ink-400">{formatTime(f.scheduled_for)}</div>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {tab === "symptoms" && (
        <div className="card p-5">
          {symptoms.length === 0 && (
            <p className="text-sm text-ink-400">
              No symptoms reported yet. Symptoms the patient shares over WhatsApp are
              captured here automatically.
            </p>
          )}
          <div className="space-y-3">
            {symptoms.map((s) => (
              <div
                key={s.id}
                className="flex items-start gap-3 rounded-xl border border-black/[0.05] p-3"
              >
                <div className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-full bg-rose-50 text-rose-600">
                  <Icon.pulse width={15} height={15} />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className={`pill ${SEV_COLOR[s.severity] || SEV_COLOR.unknown}`}>
                      {s.severity}
                    </span>
                    <span className="text-[11px] text-ink-400">
                      {timeAgo(s.reported_at)} · via {s.source}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-ink-800">{s.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "followups" && (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <tbody>
              {followups.map((f) => (
                <tr key={f.id} className="border-b border-black/[0.04] last:border-0">
                  <td className="px-5 py-3 font-medium text-ink-900">{f.title}</td>
                  <td className="px-5 py-3 text-ink-500">{f.kind}</td>
                  <td className="px-5 py-3 text-ink-500">{formatTime(f.scheduled_for)}</td>
                  <td className="px-5 py-3">{statusPill(f.status)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "messages" && (
        <div className="card flex h-[500px] flex-col p-5">
          <div className="mb-3 flex items-center justify-between border-b border-black/[0.06] pb-3">
            <div className="text-xs text-ink-400">
              WhatsApp · replies are AI-assisted follow-ups
            </div>
            <button
              onClick={aiCheckin}
              disabled={busy}
              className="flex items-center gap-1.5 rounded-lg border border-brand-200 bg-brand-50 px-3 py-1.5 text-xs font-semibold text-brand-700 hover:bg-brand-100 disabled:opacity-60"
            >
              <Icon.bolt width={13} height={13} />
              {busy ? "Sending…" : "AI symptom check-in"}
            </button>
          </div>
          <div className="flex-1 space-y-3 overflow-y-auto pr-1">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex ${m.direction === "outbound" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm ${
                    m.direction === "outbound"
                      ? "bg-brand-500 text-white"
                      : "bg-gray-100 text-ink-800"
                  }`}
                >
                  {m.direction === "inbound" && (
                    <div className="mb-1">{categoryPill(m.category)}</div>
                  )}
                  <p>{m.body}</p>
                  <div
                    className={`mt-1 text-[10px] ${
                      m.direction === "outbound" ? "text-white/60" : "text-ink-400"
                    }`}
                  >
                    {timeAgo(m.created_at)}
                  </div>
                </div>
              </div>
            ))}
            {messages.length === 0 && (
              <p className="text-sm text-ink-400">No WhatsApp messages yet.</p>
            )}
          </div>
          {chatErr && (
            <div className="mt-2 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-600">
              {chatErr}
            </div>
          )}
          <div className="mt-3 flex gap-2">
            <input
              value={reply}
              onChange={(e) => setReply(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendReply()}
              placeholder="Reply on WhatsApp…"
              className="flex-1 rounded-xl border border-black/10 px-3.5 py-2.5 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
            />
            <button
              onClick={sendReply}
              className="flex items-center gap-1.5 rounded-xl bg-brand-500 px-4 text-sm font-semibold text-white hover:bg-brand-600"
            >
              <Icon.send width={15} height={15} stroke="white" /> Send
            </button>
          </div>
        </div>
      )}

      {tab === "notes" && (
        <div className="card p-5">
          <div className="mb-4 flex gap-2">
            <input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addNote()}
              placeholder="Add a clinical note…"
              className="flex-1 rounded-xl border border-black/10 px-3.5 py-2.5 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
            />
            <button
              onClick={addNote}
              className="rounded-xl bg-brand-500 px-4 text-sm font-semibold text-white hover:bg-brand-600"
            >
              Add
            </button>
          </div>
          <div className="space-y-3">
            {notes.map((n) => (
              <div key={n.id} className="rounded-xl border border-black/[0.06] p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-ink-900">{n.author}</span>
                  <span className="text-[11px] text-ink-400">{timeAgo(n.created_at)}</span>
                </div>
                <p className="mt-1 text-sm text-ink-600">{n.body}</p>
              </div>
            ))}
            {notes.length === 0 && (
              <p className="text-sm text-ink-400">No notes yet.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
