"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import PageHeader from "@/components/PageHeader";
import { Icon } from "@/components/icons";
import { Avatar, riskPill } from "@/lib/ui";
import { api, Patient } from "@/lib/api";
import AddPatientModal from "@/components/AddPatientModal";

export default function PatientsPage() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [q, setQ] = useState("");
  const [risk, setRisk] = useState<string>("all");
  const [showAdd, setShowAdd] = useState(false);

  function load() {
    api.patients().then(setPatients).catch(() => {});
  }
  useEffect(load, []);

  const filtered = patients.filter((p) => {
    const matchesQ =
      !q ||
      p.name.toLowerCase().includes(q.toLowerCase()) ||
      p.mrn.toLowerCase().includes(q.toLowerCase()) ||
      p.cancer_type.toLowerCase().includes(q.toLowerCase());
    const matchesRisk = risk === "all" || p.risk === risk;
    return matchesQ && matchesRisk;
  });

  return (
    <div>
      <PageHeader
        title="Patients"
        subtitle={`${patients.length} oncology patients under your care`}
        right={
          <button
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-2 rounded-xl bg-brand-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-600"
          >
            <Icon.users width={15} height={15} stroke="white" /> Add patient
          </button>
        }
      />

      {showAdd && (
        <AddPatientModal onClose={() => setShowAdd(false)} onCreated={load} />
      )}

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[220px]">
          <Icon.search
            width={16}
            height={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-400"
          />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search by name, MRN or diagnosis…"
            className="w-full rounded-xl border border-black/10 bg-white py-2.5 pl-9 pr-3 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
          />
        </div>
        <div className="flex gap-1 rounded-xl bg-white p-1 shadow-soft">
          {["all", "high", "medium", "low"].map((r) => (
            <button
              key={r}
              onClick={() => setRisk(r)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium capitalize transition ${
                risk === r
                  ? "bg-brand-500 text-white"
                  : "text-ink-500 hover:bg-black/5"
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-black/[0.06] text-left text-[11px] uppercase tracking-wider text-ink-400">
              <th className="px-5 py-3 font-semibold">Patient</th>
              <th className="px-5 py-3 font-semibold">Diagnosis</th>
              <th className="px-5 py-3 font-semibold">Stage</th>
              <th className="px-5 py-3 font-semibold">Regimen</th>
              <th className="px-5 py-3 font-semibold">Status</th>
              <th className="px-5 py-3 font-semibold">Risk</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((p) => (
              <tr
                key={p.id}
                className="group border-b border-black/[0.04] last:border-0 hover:bg-brand-50/40"
              >
                <td className="px-5 py-3">
                  <Link href={`/patients/${p.id}`} className="flex items-center gap-3">
                    <Avatar name={p.name} />
                    <div>
                      <div className="font-medium text-ink-900 group-hover:text-brand-700">
                        {p.name}
                      </div>
                      <div className="text-xs text-ink-400">
                        {p.mrn} · {p.age}/{p.sex[0]}
                      </div>
                    </div>
                  </Link>
                </td>
                <td className="px-5 py-3 text-ink-700">{p.cancer_type}</td>
                <td className="px-5 py-3">
                  <span className="pill bg-gray-100 text-ink-700">{p.stage}</span>
                </td>
                <td className="px-5 py-3 text-ink-500">{p.regimen}</td>
                <td className="px-5 py-3 text-ink-700">{p.status}</td>
                <td className="px-5 py-3">{riskPill(p.risk)}</td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="px-5 py-10 text-center text-ink-400">
                  No patients match your filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
