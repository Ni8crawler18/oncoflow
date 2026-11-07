"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import PageHeader from "@/components/PageHeader";
import { Icon } from "@/components/icons";
import { statusPill, formatTime } from "@/lib/ui";
import { api, FollowUp } from "@/lib/api";

export default function ImagingPage() {
  const [items, setItems] = useState<FollowUp[]>([]);
  useEffect(() => {
    Promise.all([
      api.followups("scheduled"),
      api.followups("completed"),
    ])
      .then(([a, b]) =>
        setItems(
          [...a, ...b].filter((f) => f.kind === "imaging").sort((x, y) =>
            y.scheduled_for.localeCompare(x.scheduled_for)
          )
        )
      )
      .catch(() => {});
  }, []);

  return (
    <div>
      <PageHeader
        title="Imaging & Restaging"
        subtitle="Scheduled and completed restaging scans across your patients."
      />
      <div className="card overflow-hidden">
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
            {items.map((f) => (
              <tr key={f.id} className="border-b border-black/[0.04] last:border-0 hover:bg-brand-50/40">
                <td className="px-5 py-3">
                  <Link href={`/patients/${f.patient_id}`} className="font-medium text-ink-900 hover:text-brand-700">
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
            {items.length === 0 && (
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
