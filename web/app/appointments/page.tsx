"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import PageHeader from "@/components/PageHeader";
import { Icon } from "@/components/icons";
import { statusPill } from "@/lib/ui";
import { api, FollowUp } from "@/lib/api";

const KIND_COLOR: Record<string, string> = {
  chemo: "bg-violet-100 text-violet-700",
  imaging: "bg-emerald-100 text-emerald-700",
  labs: "bg-sky-100 text-sky-700",
  review: "bg-brand-100 text-brand-700",
  consult: "bg-amber-100 text-amber-700",
};

function ymd(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
    d.getDate()
  ).padStart(2, "0")}`;
}

export default function AppointmentsPage() {
  const [items, setItems] = useState<FollowUp[]>([]);
  const [cursor, setCursor] = useState(() => {
    const d = new Date();
    return new Date(d.getFullYear(), d.getMonth(), 1);
  });
  const [selected, setSelected] = useState<string>(ymd(new Date()));
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  function load() {
    api.allFollowups().then(setItems).catch(() => {});
  }
  useEffect(load, []);

  async function runAuto() {
    setBusy(true);
    setMsg("");
    try {
      const r = await api.autoSchedule();
      setMsg(
        `Auto-scheduled ${r.created} new appointment${r.created !== 1 ? "s" : ""}.`
      );
      load();
    } catch {
      setMsg("Auto-schedule failed.");
    } finally {
      setBusy(false);
    }
  }

  // group by day
  const byDay = useMemo(() => {
    const m: Record<string, FollowUp[]> = {};
    for (const f of items) {
      const key = f.scheduled_for.slice(0, 10);
      (m[key] ||= []).push(f);
    }
    return m;
  }, [items]);

  // build calendar grid (6 weeks) starting Sunday
  const grid = useMemo(() => {
    const first = new Date(cursor.getFullYear(), cursor.getMonth(), 1);
    const start = new Date(first);
    start.setDate(first.getDate() - first.getDay());
    return Array.from({ length: 42 }, (_, i) => {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      return d;
    });
  }, [cursor]);

  const monthLabel = cursor.toLocaleString(undefined, {
    month: "long",
    year: "numeric",
  });
  const todayKey = ymd(new Date());
  const selectedItems = (byDay[selected] || []).sort((a, b) =>
    a.scheduled_for.localeCompare(b.scheduled_for)
  );

  return (
    <div>
      <PageHeader
        title="Appointments"
        subtitle="Every follow-up across your patient panel, on one calendar."
        right={
          <button
            onClick={runAuto}
            disabled={busy}
            className="flex items-center gap-2 rounded-xl bg-brand-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-600 disabled:opacity-60"
          >
            <Icon.bolt width={15} height={15} stroke="white" />
            {busy ? "Scheduling…" : "Auto-schedule follow-ups"}
          </button>
        }
      />
      {msg && <div className="mb-4 text-sm text-emerald-600">{msg}</div>}

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        {/* Calendar */}
        <div className="card p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-ink-900">{monthLabel}</h2>
            <div className="flex gap-1">
              <button
                onClick={() =>
                  setCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1))
                }
                className="rounded-lg px-2.5 py-1 text-sm text-ink-500 hover:bg-black/5"
              >
                ‹
              </button>
              <button
                onClick={() => {
                  const d = new Date();
                  setCursor(new Date(d.getFullYear(), d.getMonth(), 1));
                  setSelected(ymd(d));
                }}
                className="rounded-lg px-3 py-1 text-xs font-medium text-ink-600 hover:bg-black/5"
              >
                Today
              </button>
              <button
                onClick={() =>
                  setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1))
                }
                className="rounded-lg px-2.5 py-1 text-sm text-ink-500 hover:bg-black/5"
              >
                ›
              </button>
            </div>
          </div>

          <div className="grid grid-cols-7 gap-1 text-center text-[11px] font-semibold uppercase tracking-wider text-ink-400">
            {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
              <div key={d} className="py-1">
                {d}
              </div>
            ))}
          </div>
          <div className="mt-1 grid grid-cols-7 gap-1">
            {grid.map((d) => {
              const key = ymd(d);
              const inMonth = d.getMonth() === cursor.getMonth();
              const dayItems = byDay[key] || [];
              const isSel = key === selected;
              const isToday = key === todayKey;
              return (
                <button
                  key={key}
                  onClick={() => setSelected(key)}
                  className={`flex min-h-[72px] flex-col items-start rounded-lg border p-1.5 text-left transition ${
                    isSel
                      ? "border-brand-400 bg-brand-50"
                      : "border-black/[0.05] hover:bg-black/[0.02]"
                  } ${inMonth ? "" : "opacity-40"}`}
                >
                  <span
                    className={`mb-1 flex h-5 w-5 items-center justify-center rounded-full text-xs ${
                      isToday ? "bg-brand-500 font-semibold text-white" : "text-ink-600"
                    }`}
                  >
                    {d.getDate()}
                  </span>
                  <div className="flex w-full flex-col gap-0.5">
                    {dayItems.slice(0, 2).map((f) => (
                      <span
                        key={f.id}
                        className={`truncate rounded px-1 py-0.5 text-[10px] font-medium ${
                          KIND_COLOR[f.kind] || "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {f.patient_name}
                      </span>
                    ))}
                    {dayItems.length > 2 && (
                      <span className="px-1 text-[10px] text-ink-400">
                        +{dayItems.length - 2} more
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Day detail */}
        <div className="card h-fit p-5">
          <h2 className="text-sm font-semibold text-ink-900">
            {new Date(selected + "T00:00:00").toLocaleDateString(undefined, {
              weekday: "long",
              month: "short",
              day: "numeric",
            })}
          </h2>
          <p className="mb-4 text-xs text-ink-400">
            {selectedItems.length} appointment{selectedItems.length !== 1 ? "s" : ""}
          </p>
          <div className="space-y-2">
            {selectedItems.map((f) => (
              <Link
                key={f.id}
                href={`/patients/${f.patient_id}`}
                className="block rounded-xl border border-black/[0.05] p-3 transition hover:bg-brand-50/40"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-ink-900">
                    {f.patient_name}
                  </span>
                  <span className="text-xs font-medium text-ink-600">
                    {new Date(f.scheduled_for).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
                <div className="mt-1 flex items-center gap-2">
                  <span
                    className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                      KIND_COLOR[f.kind] || "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {f.kind}
                  </span>
                  {statusPill(f.status)}
                </div>
              </Link>
            ))}
            {selectedItems.length === 0 && (
              <p className="text-sm text-ink-400">No appointments this day.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
