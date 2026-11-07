"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import PageHeader from "@/components/PageHeader";
import { Icon } from "@/components/icons";
import { Avatar, categoryPill, timeAgo } from "@/lib/ui";
import { api, Message, Patient } from "@/lib/api";

export default function MessagesPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    api.messages().then(setMessages).catch(() => {});
    api.patients().then(setPatients).catch(() => {});
  }, []);

  const nameFor = useMemo(() => {
    const m = new Map(patients.map((p) => [p.id, p.name]));
    return (id: number) => m.get(id) || `Patient #${id}`;
  }, [patients]);

  const inbound = messages.filter((m) => m.direction === "inbound");
  const filtered = inbound.filter((m) => filter === "all" || m.category === filter);

  return (
    <div>
      <PageHeader
        title="Telegram Inbox"
        subtitle="Patient messages are auto-classified and filed under each patient."
        right={
          <div className="flex items-center gap-2 rounded-full bg-white px-3 py-1.5 text-sm shadow-soft">
            <Icon.telegram width={16} height={16} />
            <span className="font-medium text-ink-700">Telegram</span>
          </div>
        }
      />

      <div className="mb-4 flex gap-1 rounded-xl bg-white p-1 shadow-soft w-fit">
        {[
          ["all", "All"],
          ["symptom", "Symptoms"],
          ["feedback", "Feedback"],
          ["general", "General"],
        ].map(([f, label]) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`rounded-lg px-4 py-1.5 text-sm font-medium transition ${
              filter === f ? "bg-brand-500 text-white" : "text-ink-500 hover:bg-black/5"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="card divide-y divide-black/[0.05]">
        {filtered.map((m) => (
          <Link
            key={m.id}
            href={`/patients/${m.patient_id}`}
            className="flex items-start gap-3 p-4 transition hover:bg-brand-50/40"
          >
            <Avatar name={nameFor(m.patient_id)} />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-ink-900">
                  {nameFor(m.patient_id)}
                </span>
                {categoryPill(m.category)}
              </div>
              <p className="mt-0.5 truncate text-sm text-ink-600">{m.body}</p>
            </div>
            <span className="whitespace-nowrap text-[11px] text-ink-400">
              {timeAgo(m.created_at)}
            </span>
          </Link>
        ))}
        {filtered.length === 0 && (
          <p className="p-8 text-center text-sm text-ink-400">No messages here.</p>
        )}
      </div>
    </div>
  );
}
