"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import PageHeader from "@/components/PageHeader";
import { Avatar, riskPill } from "@/lib/ui";
import { api, Patient } from "@/lib/api";

export default function TreatmentTracker() {
  const [patients, setPatients] = useState<Patient[]>([]);
  useEffect(() => {
    api.patients().then(setPatients).catch(() => {});
  }, []);

  const byRegimen = patients.reduce<Record<string, Patient[]>>((acc, p) => {
    (acc[p.regimen] ||= []).push(p);
    return acc;
  }, {});

  return (
    <div>
      <PageHeader
        title="Treatment Tracker"
        subtitle="Active oncology patients grouped by chemotherapy regimen."
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
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {list.map((p) => (
                <Link
                  key={p.id}
                  href={`/patients/${p.id}`}
                  className="flex items-center gap-3 rounded-xl border border-black/[0.05] p-3 transition hover:bg-brand-50/40"
                >
                  <Avatar name={p.name} />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium text-ink-900">
                      {p.name}
                    </div>
                    <div className="truncate text-xs text-ink-400">
                      {p.cancer_type} · {p.stage} · {p.treatment_line}
                    </div>
                  </div>
                  {riskPill(p.risk)}
                </Link>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
