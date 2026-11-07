"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import PageHeader from "@/components/PageHeader";
import { Avatar, riskPill } from "@/lib/ui";
import { api, Patient, FollowUp } from "@/lib/api";

type Row = Patient & {
  cycles: number;
  next: FollowUp | null;
  overdue: boolean;
};

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
  });
}

export default function TreatmentTracker() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [followups, setFollowups] = useState<FollowUp[]>([]);

  useEffect(() => {
    api.patients().then(setPatients).catch(() => {});
    api.allFollowups().then(setFollowups).catch(() => {});
  }, []);

  const rows = useMemo<Row[]>(() => {
    const now = Date.now();
    return patients.map((p) => {
      const fus = followups.filter((f) => f.patient_id === p.id);
      const cycles = fus.filter((f) => f.status === "completed").length;
      const upcoming = fus
        .filter((f) => f.status === "scheduled" && new Date(f.scheduled_for).getTime() >= now)
        .sort((a, b) => a.scheduled_for.localeCompare(b.scheduled_for));
      const overdue = fus.some(
        (f) => f.status === "scheduled" && new Date(f.scheduled_for).getTime() < now
      );
      return { ...p, cycles, next: upcoming[0] || null, overdue };
    });
  }, [patients, followups]);

  // Sort by regimen (keeps same-regimen patients adjacent), then by name.
  const sorted = useMemo(
    () =>
      [...rows].sort(
        (a, b) =>
          (a.regimen || "").localeCompare(b.regimen || "") ||
          a.name.localeCompare(b.name)
      ),
    [rows]
  );

  return (
    <div>
      <PageHeader
        title="Treatment Tracker"
        subtitle="Where every patient stands on their chemotherapy course — cycles completed, the next visit due, and who has fallen behind."
      />
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-black/[0.06] text-left text-[11px] uppercase tracking-wider text-ink-400">
              <th className="px-5 py-3 font-semibold">Patient</th>
              <th className="px-5 py-3 font-semibold">Regimen</th>
              <th className="px-5 py-3 font-semibold">Cycles done</th>
              <th className="px-5 py-3 font-semibold">Next visit</th>
              <th className="px-5 py-3 text-right font-semibold">Risk</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((p) => (
              <tr
                key={p.id}
                className="border-b border-black/[0.04] last:border-0 hover:bg-brand-50/40"
              >
                <td className="px-5 py-3">
                  <Link href={`/patients/${p.id}`} className="flex items-center gap-3">
                    <Avatar name={p.name} />
                    <div className="min-w-0">
                      <div className="truncate font-medium text-ink-900">{p.name}</div>
                      <div className="truncate text-xs text-ink-400">
                        {p.cancer_type} · {p.stage} · {p.treatment_line}
                      </div>
                    </div>
                  </Link>
                </td>
                <td className="px-5 py-3 text-ink-600">{p.regimen || "—"}</td>
                <td className="px-5 py-3 text-ink-700">{p.cycles}</td>
                <td className="px-5 py-3">
                  {p.overdue ? (
                    <span className="pill bg-rose-50 text-rose-600">Overdue</span>
                  ) : p.next ? (
                    <span className="text-ink-700">
                      {p.next.kind} · {fmtDate(p.next.scheduled_for)}
                    </span>
                  ) : (
                    <span className="pill bg-amber-50 text-amber-600">
                      Needs scheduling
                    </span>
                  )}
                </td>
                <td className="px-5 py-3 text-right">{riskPill(p.risk)}</td>
              </tr>
            ))}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={5} className="px-5 py-10 text-center text-ink-400">
                  No patients on treatment yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
