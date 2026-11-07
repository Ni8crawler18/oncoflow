"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import PageHeader from "@/components/PageHeader";
import { Icon } from "@/components/icons";
import { statusPill, formatTime } from "@/lib/ui";
import { api, FollowUp, Patient } from "@/lib/api";

export default function SchedulePage() {
  const [followups, setFollowups] = useState<FollowUp[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [slots, setSlots] = useState<string[]>([]);
  const [day, setDay] = useState(new Date().toISOString().slice(0, 10));
  const [patientId, setPatientId] = useState<number | "">("");
  const [kind, setKind] = useState("review");
  const [picked, setPicked] = useState<string | null>(null);
  const [msg, setMsg] = useState("");

  function load() {
    api.followups("scheduled").then(setFollowups).catch(() => {});
  }
  useEffect(() => {
    load();
    api.patients().then(setPatients).catch(() => {});
  }, []);

  useEffect(() => {
    api.slots(day).then((r) => setSlots(r.slots)).catch(() => setSlots([]));
    setPicked(null);
  }, [day]);

  async function book() {
    setMsg("");
    if (!patientId || !picked) {
      setMsg("Pick a patient and an open slot.");
      return;
    }
    try {
      await api.createFollowup({
        patient_id: Number(patientId),
        kind,
        title: `${kind[0].toUpperCase() + kind.slice(1)} appointment`,
        scheduled_for: picked,
        duration_min: kind === "chemo" ? 60 : 30,
        priority: "normal",
      });
      setMsg("✓ Booked. No scheduling conflicts.");
      load();
      api.slots(day).then((r) => setSlots(r.slots));
      setPicked(null);
    } catch (e: any) {
      setMsg(e.message?.includes("409") ? "Conflict: slot taken." : "Could not book.");
    }
  }

  const now = Date.now();
  const overdue = followups.filter((f) => new Date(f.scheduled_for).getTime() < now);
  const upcoming = followups.filter((f) => new Date(f.scheduled_for).getTime() >= now);

  return (
    <div>
      <PageHeader
        title="Follow-ups & Schedule"
        subtitle="Conflict-free scheduling that makes the most of clinic time."
      />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        {/* Booking panel */}
        <div className="card h-fit p-5">
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-ink-900">
            <Icon.bolt width={16} height={16} className="text-brand-500" /> Book a
            follow-up
          </div>

          <label className="mb-1.5 block text-xs font-medium text-ink-700">Patient</label>
          <select
            value={patientId}
            onChange={(e) => setPatientId(e.target.value ? Number(e.target.value) : "")}
            className="mb-3 w-full rounded-xl border border-black/10 bg-white px-3 py-2.5 text-sm outline-none focus:border-brand-400"
          >
            <option value="">Select patient…</option>
            {patients.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} · {p.cancer_type}
              </option>
            ))}
          </select>

          <label className="mb-1.5 block text-xs font-medium text-ink-700">Type</label>
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value)}
            className="mb-3 w-full rounded-xl border border-black/10 bg-white px-3 py-2.5 text-sm outline-none focus:border-brand-400"
          >
            {["review", "chemo", "imaging", "labs", "consult"].map((k) => (
              <option key={k} value={k}>
                {k[0].toUpperCase() + k.slice(1)}
              </option>
            ))}
          </select>

          <label className="mb-1.5 block text-xs font-medium text-ink-700">Day</label>
          <input
            type="date"
            value={day}
            onChange={(e) => setDay(e.target.value)}
            className="mb-3 w-full rounded-xl border border-black/10 bg-white px-3 py-2.5 text-sm outline-none focus:border-brand-400"
          />

          <label className="mb-1.5 block text-xs font-medium text-ink-700">
            Open slots (conflict-free)
          </label>
          <div className="mb-4 grid grid-cols-3 gap-2">
            {slots.map((s) => {
              const t = new Date(s).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              });
              return (
                <button
                  key={s}
                  onClick={() => setPicked(s)}
                  className={`rounded-lg border px-2 py-1.5 text-xs font-medium transition ${
                    picked === s
                      ? "border-brand-500 bg-brand-500 text-white"
                      : "border-black/10 text-ink-600 hover:border-brand-300"
                  }`}
                >
                  {t}
                </button>
              );
            })}
            {slots.length === 0 && (
              <p className="col-span-3 text-xs text-ink-400">No open slots this day.</p>
            )}
          </div>

          <button
            onClick={book}
            className="w-full rounded-xl bg-brand-500 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-600"
          >
            Book follow-up
          </button>
          {msg && (
            <p
              className={`mt-2 text-xs ${
                msg.startsWith("✓") ? "text-emerald-600" : "text-rose-600"
              }`}
            >
              {msg}
            </p>
          )}
        </div>

        {/* Lists */}
        <div className="space-y-5 lg:col-span-2">
          <div className="card p-5">
            <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-rose-600">
              <Icon.pulse width={16} height={16} /> Overdue ({overdue.length})
            </div>
            <List items={overdue} empty="Nothing overdue. Great continuity of care." />
          </div>

          <div className="card p-5">
            <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-ink-900">
              <Icon.calendar width={16} height={16} className="text-brand-500" />{" "}
              Upcoming ({upcoming.length})
            </div>
            <List items={upcoming} empty="No upcoming follow-ups scheduled." />
          </div>
        </div>
      </div>
    </div>
  );
}

function List({ items, empty }: { items: FollowUp[]; empty: string }) {
  if (items.length === 0)
    return <p className="text-sm text-ink-400">{empty}</p>;
  return (
    <div className="space-y-2">
      {items
        .sort((a, b) => a.scheduled_for.localeCompare(b.scheduled_for))
        .map((f) => (
          <Link
            key={f.id}
            href={`/patients/${f.patient_id}`}
            className="flex items-center justify-between rounded-xl border border-black/[0.05] px-4 py-3 transition hover:bg-brand-50/40"
          >
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-ink-900">
                  {f.patient_name}
                </span>
                {f.priority === "high" && (
                  <span className="pill bg-rose-50 text-rose-600">High priority</span>
                )}
              </div>
              <div className="text-xs text-ink-400">
                {f.title} · {f.cancer_type}
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm font-medium text-ink-700">
                {formatTime(f.scheduled_for)}
              </div>
              <div className="text-xs text-ink-400">{f.duration_min} min</div>
            </div>
          </Link>
        ))}
    </div>
  );
}
