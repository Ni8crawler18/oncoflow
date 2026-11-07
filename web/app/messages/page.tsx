"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import PageHeader from "@/components/PageHeader";
import { Icon } from "@/components/icons";
import { Avatar, categoryPill, timeAgo } from "@/lib/ui";
import { api, Message, Patient, CheckinRun } from "@/lib/api";

export default function MessagesPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [filter, setFilter] = useState("all");
  const [busy, setBusy] = useState(false);
  const [run, setRun] = useState<CheckinRun | null>(null);

  function load() {
    api.messages().then(setMessages).catch(() => {});
    api.patients().then(setPatients).catch(() => {});
  }
  useEffect(load, []);

  async function runCheckins() {
    setBusy(true);
    try {
      const r = await api.runCheckins();
      setRun(r);
      load();
    } catch {
      /* ignore */
    } finally {
      setBusy(false);
    }
  }

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
          <button
            onClick={runCheckins}
            disabled={busy}
            className="flex items-center gap-2 rounded-xl bg-brand-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-600 disabled:opacity-60"
          >
            <Icon.bolt width={15} height={15} stroke="white" />
            {busy ? "Sending…" : "Run AI check-ins"}
          </button>
        }
      />

      {run && (
        <div className="card mb-4 p-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-ink-900">
              {run.sent > 0
                ? `Sent ${run.sent} AI check-in${run.sent !== 1 ? "s" : ""}`
                : "No check-ins were due"}
            </h2>
            <button
              onClick={() => setRun(null)}
              className="text-xs text-ink-400 hover:text-ink-700"
            >
              Dismiss
            </button>
          </div>
          <p className="mt-1 text-xs text-ink-500">
            {run.not_due} patient{run.not_due !== 1 ? "s" : ""} contacted recently
            (not due){run.unlinked > 0 && (
              <>
                {" · "}
                <span className="text-amber-600">
                  {run.unlinked} not on Telegram yet — onboard them to enable
                  check-ins
                </span>
              </>
            )}
            .
          </p>
          {run.items.length > 0 && (
            <div className="mt-3 space-y-2">
              {run.items.map((it) => (
                <Link
                  key={it.patient_id}
                  href={`/patients/${it.patient_id}`}
                  className="block rounded-xl border border-black/[0.05] p-3 transition hover:bg-brand-50/40"
                >
                  <div className="text-sm font-medium text-ink-900">
                    {it.patient_name}
                  </div>
                  <p className="mt-0.5 text-xs text-ink-500">“{it.body}”</p>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}

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
