"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import PageHeader from "@/components/PageHeader";
import { Icon } from "@/components/icons";
import { Avatar, timeAgo } from "@/lib/ui";
import { api, SymptomFeed } from "@/lib/api";

const SEV_COLOR: Record<string, string> = {
  severe: "bg-rose-50 text-rose-600",
  moderate: "bg-amber-50 text-amber-600",
  mild: "bg-emerald-50 text-emerald-600",
  unknown: "bg-gray-100 text-gray-500",
};

export default function SafetyPage() {
  const [symptoms, setSymptoms] = useState<SymptomFeed[]>([]);

  useEffect(() => {
    api.symptomsFeed().then(setSymptoms).catch(() => {});
  }, []);

  const severe = symptoms.filter((s) => s.severity === "severe").length;

  return (
    <div>
      <PageHeader
        title="Safety & Toxicity"
        subtitle="Patient-reported symptoms captured from Telegram, flagged for triage."
      />

      <div className="mb-5 card border-l-4 border-l-rose-400 p-4">
        <div className="flex items-center gap-2 text-sm text-ink-700">
          <Icon.shield width={16} height={16} className="text-rose-500" />
          <span className="font-semibold">{symptoms.length} reported symptoms</span>
          <span className="text-ink-400">
            · {severe} flagged severe. Review and escalate as needed.
          </span>
        </div>
      </div>

      <div className="space-y-3">
        {symptoms.map((s) => (
          <Link
            key={s.id}
            href={`/patients/${s.patient_id}`}
            className="card flex items-start gap-3 p-4 transition hover:bg-rose-50/30"
          >
            <Avatar name={s.patient_name} />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-ink-900">
                  {s.patient_name}
                </span>
                <span className={`pill ${SEV_COLOR[s.severity] || SEV_COLOR.unknown}`}>
                  {s.severity}
                </span>
                <span className="pill bg-gray-100 text-ink-600">
                  {s.cancer_type}
                </span>
              </div>
              <p className="mt-1 text-sm text-rose-700">{s.description}</p>
            </div>
            <span className="whitespace-nowrap text-[11px] text-ink-400">
              {timeAgo(s.reported_at)}
            </span>
          </Link>
        ))}
        {symptoms.length === 0 && (
          <p className="card p-8 text-center text-sm text-ink-400">
            No symptoms reported yet. They appear here as patients message over Telegram.
          </p>
        )}
      </div>
    </div>
  );
}
