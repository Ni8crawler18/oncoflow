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

  const byRegimen = useMemo(() => {
    return rows.reduce<Record<string, Row[]>>((acc, r) => {
      (acc[r.regimen || "Unassigned regimen"] ||= []).push(r);
      return acc;
    }, {});
  }, [rows]);

  return (
    <div>
      <PageHeader
        title="Treatment Tracker"
        subtitle="Where every patient stands on their chemotherapy course — cycles completed, the next visit due, and who has fallen behind."
      />
      <div className="space-y-5">
        {Object.entries(byRegimen).map(([regimen, list]) => (
          <div key={regimen} className="card p-5">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-ink-900">{regimen}</h2>
              <span className="pill bg-brand-50 text-brand-600">
                {list.length} patient{list.length > 1 ? "s" : ""}
              </span>
            </div>
            <div className="overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[11px] uppercase tracking-wider text-ink-400">
                    <th className="pb-2 font-semibold">Patient</th>
                    <th className="pb-2 font-semibold">Cycles done</th>
                    <th className="pb-2 font-semibold">Next visit</th>
                    <th className="pb-2 text-right font-semibold">Risk</th>
                  </tr>
                </thead>
                <tbody>
                  {list.map((p) => (
                    <tr
                      key={p.id}
                      className="border-t border-black/[0.04] hover:bg-brand-50/40"
                    >
                      <td className="py-2.5">
                        <Link
                          href={`/patients/${p.id}`}
                          className="flex items-center gap-3"
                        >
                          <Avatar name={p.name} />
                          <div className="min-w-0">
                            <div className="truncate font-medium text-ink-900">
                              {p.name}
                            </div>
                            <div className="truncate text-xs text-ink-400">
                              {p.cancer_type} · {p.stage} · {p.treatment_line}
                            </div>
                          </div>
                        </Link>
                      </td>
                      <td className="py-2.5 text-ink-700">{p.cycles}</td>
                      <td className="py-2.5">
                        {p.overdue ? (
                          <span className="pill bg-rose-50 text-rose-600">
                            Overdue
                          </span>
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
                      <td className="py-2.5 text-right">{riskPill(p.risk)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
