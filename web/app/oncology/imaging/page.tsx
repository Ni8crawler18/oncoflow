"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import PageHeader from "@/components/PageHeader";
import { Icon } from "@/components/icons";
import { Avatar, statusPill, formatTime } from "@/lib/ui";
import { api, FollowUp, Patient } from "@/lib/api";

// Restaging is typically reassessed roughly every ~3 cycles.
const RESTAGING_DAYS = 84;
const DAY = 86_400_000;

export default function ImagingPage() {
  const [scans, setScans] = useState<FollowUp[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);

  useEffect(() => {
    Promise.all([api.followups("scheduled"), api.followups("completed")])
      .then(([a, b]) =>
        setScans(
          [...a, ...b]
            .filter((f) => f.kind === "imaging")
            .sort((x, y) => y.scheduled_for.localeCompare(x.scheduled_for))
        )
      )
      .catch(() => {});
    api.patients().then(setPatients).catch(() => {});
  }, []);

  // Who is due (or overdue) for a restaging scan.
  const due = useMemo(() => {
    const now = Date.now();
    return patients
      .map((p) => {
        const mine = scans.filter((s) => s.patient_id === p.id);
        const upcoming = mine.some(
          (s) => s.status === "scheduled" && new Date(s.scheduled_for).getTime() >= now
        );
        if (upcoming) return null;
        const completed = mine
          .filter((s) => s.status === "completed")
          .map((s) => new Date(s.scheduled_for).getTime())
          .sort((a, b) => b - a);
        const last = completed[0];
        if (last === undefined) {
          return { patient: p, reason: "No restaging scan on record" };
        }
        const days = Math.floor((now - last) / DAY);
        if (days >= RESTAGING_DAYS) {
          return { patient: p, reason: `Last scan ${days} days ago` };
        }
        return null;
      })
      .filter((x): x is { patient: Patient; reason: string } => x !== null);
  }, [patients, scans]);

  return (
    <div>
      <PageHeader
        title="Imaging & Restaging"
        subtitle="Keep restaging on cadence — see who is due for a scan, then track every scheduled and completed restaging across your panel."
      />

      {/* Restaging due */}
      <div className="card mb-5 p-5">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-ink-900">
            Restaging due
          </h2>
          <span className="pill bg-amber-50 text-amber-600">
            {due.length} patient{due.length !== 1 ? "s" : ""}
          </span>
        </div>
        {due.length === 0 ? (
          <p className="text-sm text-ink-400">
            Everyone on the panel has a recent or upcoming restaging scan.
          </p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {due.map(({ patient, reason }) => (
              <Link
                key={patient.id}
                href={`/patients/${patient.id}`}
                className="flex items-center gap-3 rounded-xl border border-amber-200/60 bg-amber-50/40 p-3 transition hover:bg-amber-50"
              >
                <Avatar name={patient.name} />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium text-ink-900">
                    {patient.name}
                  </div>
                  <div className="truncate text-xs text-ink-500">
                    {patient.cancer_type} · {reason}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Scheduled & completed scans */}
      <div className="card overflow-hidden">
        <div className="border-b border-black/[0.06] px-5 py-3">
          <h2 className="text-sm font-semibold text-ink-900">
            Scheduled &amp; completed scans
          </h2>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-black/[0.06] text-left text-[11px] uppercase tracking-wider text-ink-400">
              <th className="px-5 py-3 font-semibold">Patient</th>
              <th className="px-5 py-3 font-semibold">Scan</th>
              <th className="px-5 py-3 font-semibold">Diagnosis</th>
              <th className="px-5 py-3 font-semibold">When</th>
              <th className="px-5 py-3 font-semibold">Status</th>
            </tr>
          </thead>
          <tbody>
            {scans.map((f) => (
              <tr
                key={f.id}
                className="border-b border-black/[0.04] last:border-0 hover:bg-brand-50/40"
              >
                <td className="px-5 py-3">
                  <Link
                    href={`/patients/${f.patient_id}`}
                    className="font-medium text-ink-900 hover:text-brand-700"
                  >
                    {f.patient_name}
                  </Link>
                </td>
                <td className="px-5 py-3 text-ink-700">
                  <span className="inline-flex items-center gap-1.5">
                    <Icon.scan width={15} height={15} className="text-brand-500" />
                    {f.title}
                  </span>
                </td>
                <td className="px-5 py-3 text-ink-500">{f.cancer_type}</td>
                <td className="px-5 py-3 text-ink-500">{formatTime(f.scheduled_for)}</td>
                <td className="px-5 py-3">{statusPill(f.status)}</td>
              </tr>
            ))}
            {scans.length === 0 && (
              <tr>
                <td colSpan={5} className="px-5 py-10 text-center text-ink-400">
                  No imaging scheduled.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
