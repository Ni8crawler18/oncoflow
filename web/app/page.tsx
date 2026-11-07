"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AreaChart,
  Area,
  ResponsiveContainer,
  Tooltip,
  XAxis,
} from "recharts";
import PageHeader from "@/components/PageHeader";
import { Icon } from "@/components/icons";
import { Avatar, categoryPill, timeAgo } from "@/lib/ui";
import { api, Stats, Activity } from "@/lib/api";
import { getUser } from "@/lib/auth";

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export default function Home() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [activity, setActivity] = useState<Activity[]>([]);
  const [trend, setTrend] = useState<{ month: string; completed: number }[]>([]);
  const [firstName, setFirstName] = useState("there");

  useEffect(() => {
    api.stats().then(setStats).catch(() => {});
    api.activity().then(setActivity).catch(() => {});
    api.trend().then(setTrend).catch(() => {});
    const u = getUser();
    if (u) {
      // "Dr. Kiran Rao" -> "Dr. Kiran"
      const parts = u.name.split(" ");
      setFirstName(parts.slice(0, 2).join(" "));
    }
  }, []);

  const statCards = [
    {
      label: "DUE TODAY",
      value: stats?.due_today ?? "-",
      hint: "follow-ups scheduled",
      icon: Icon.calendar,
      tint: "text-brand-600",
    },
    {
      label: "OVERDUE",
      value: stats?.overdue ?? "-",
      hint: "need re-engagement",
      icon: Icon.pulse,
      tint: "text-amber-600",
    },
    {
      label: "NEW SYMPTOMS",
      value: stats?.new_symptoms ?? "-",
      hint: "via Telegram",
      icon: Icon.chat,
      tint: "text-rose-600",
    },
    {
      label: "HIGH RISK",
      value: stats?.high_risk ?? "-",
      hint: "patients tracked",
      icon: Icon.shield,
      tint: "text-emerald-600",
    },
  ];

  const quickActions = [
    { label: "New Patient", icon: Icon.users, bg: "bg-sky-50", fg: "text-sky-600", href: "/patients" },
    { label: "Schedule", icon: Icon.calendar, bg: "bg-indigo-50", fg: "text-indigo-600", href: "/schedule" },
    { label: "Message", icon: Icon.send, bg: "bg-rose-50", fg: "text-rose-600", href: "/messages" },
    { label: "Treatment", icon: Icon.flask, bg: "bg-violet-50", fg: "text-violet-600", href: "/oncology/treatment" },
    { label: "Imaging", icon: Icon.scan, bg: "bg-emerald-50", fg: "text-emerald-600", href: "/oncology/imaging" },
    { label: "Analytics", icon: Icon.chart, bg: "bg-amber-50", fg: "text-amber-600", href: "/analytics" },
  ];

  return (
    <div>
      <PageHeader
        title={`${greeting()}, ${firstName}`}
        subtitle="Here's what's happening across your patients today."
      />

      {/* Hero metric card */}
      <div className="card mb-5 p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-ink-400">
              Follow-up adherence
            </div>
            <div className="mt-1 flex items-end gap-3">
              <span className="text-5xl font-bold tracking-tight text-ink-900">
                {stats ? `${stats.adherence}%` : "-"}
              </span>
            </div>
            <div className="mt-1 text-xs text-ink-400">
              Completed follow-ups across all patients, last 6 months
            </div>
          </div>
          <span className="pill bg-amber-50 text-amber-600">
            <Icon.trophy width={14} height={14} /> On track
          </span>
        </div>

        <div className="mt-4 h-40">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={trend} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#635bff" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#635bff" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="month"
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 11, fill: "#8a93a3" }}
              />
              <Tooltip
                contentStyle={{
                  borderRadius: 12,
                  border: "1px solid rgba(0,0,0,0.06)",
                  fontSize: 12,
                  boxShadow: "0 8px 24px rgba(16,18,27,0.08)",
                }}
              />
              <Area
                type="monotone"
                dataKey="completed"
                stroke="#635bff"
                strokeWidth={2.5}
                fill="url(#g)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Banner — only an alert when there's something to act on */}
      {(stats?.overdue ?? 0) > 0 ? (
        <div className="card mb-5 flex items-center justify-between p-4">
          <div className="flex items-center gap-3">
            <span className="text-xl">🎯</span>
            <p className="text-sm text-ink-700">
              <span className="font-semibold">
                {stats?.overdue} patient{stats?.overdue !== 1 ? "s" : ""}
              </span>{" "}
              overdue for follow-up. Re-engage them before they're lost to care.
            </p>
          </div>
          <Link
            href="/schedule"
            className="rounded-xl bg-brand-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-600"
          >
            Review
          </Link>
        </div>
      ) : (
        <div className="card mb-5 flex items-center gap-3 p-4">
          <span className="text-xl">✅</span>
          <p className="text-sm text-ink-700">
            <span className="font-semibold">No patients overdue.</span> Everyone on
            your panel has an upcoming or recent follow-up.
          </p>
        </div>
      )}

      {/* Stat cards */}
      <div className="mb-5 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {statCards.map((c) => {
          const I = c.icon;
          return (
            <div key={c.label} className="card p-4">
              <div className={`flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider ${c.tint}`}>
                <I width={14} height={14} /> {c.label}
              </div>
              <div className="mt-2 text-2xl font-bold text-ink-900">{c.value}</div>
              <div className="mt-0.5 text-xs text-ink-400">{c.hint}</div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        {/* Quick actions */}
        <div className="card p-5 lg:col-span-2">
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-ink-900">
            <Icon.bolt width={16} height={16} className="text-brand-500" /> Quick
            actions
          </div>
          <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
            {quickActions.map((q) => {
              const I = q.icon;
              return (
                <Link
                  key={q.label}
                  href={q.href}
                  className={`flex flex-col items-center gap-2 rounded-xl ${q.bg} p-4 text-center transition hover:scale-[1.03]`}
                >
                  <I width={20} height={20} className={q.fg} />
                  <span className="text-xs font-medium text-ink-700">
                    {q.label}
                  </span>
                </Link>
              );
            })}
          </div>
        </div>

        {/* Recent activity */}
        <div className="card p-5">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-sm font-semibold text-ink-900">
              Recent activity
            </span>
            <Link href="/messages" className="text-xs font-medium text-brand-600">
              View all
            </Link>
          </div>
          <div className="space-y-3">
            {activity.slice(0, 6).map((a, i) => (
              <div key={i} className="flex items-start gap-3">
                <Avatar name={a.patient_name} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-sm font-medium text-ink-900">
                      {a.patient_name}
                    </span>
                    {categoryPill(a.category)}
                  </div>
                  <p className="truncate text-xs text-ink-500">{a.body}</p>
                </div>
                <span className="whitespace-nowrap text-[11px] text-ink-400">
                  {timeAgo(a.created_at)}
                </span>
              </div>
            ))}
            {activity.length === 0 && (
              <p className="text-sm text-ink-400">No recent activity.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
