"use client";

import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from "recharts";
import PageHeader from "@/components/PageHeader";
import { api, Patient, Stats } from "@/lib/api";

export default function AnalyticsPage() {
  const [trend, setTrend] = useState<{ month: string; completed: number }[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    api.trend().then(setTrend).catch(() => {});
    api.patients().then(setPatients).catch(() => {});
    api.stats().then(setStats).catch(() => {});
  }, []);

  const riskCounts = ["high", "medium", "low"].map((r) => ({
    risk: r,
    count: patients.filter((p) => p.risk === r).length,
  }));
  const riskColors: Record<string, string> = {
    high: "#f43f5e",
    medium: "#f59e0b",
    low: "#10b981",
  };

  const kpis = [
    ["Patients", stats?.total_patients],
    ["Follow-up adherence", stats ? `${stats.adherence}%` : "-"],
    ["High risk", stats?.high_risk],
    ["Overdue", stats?.overdue],
  ];

  return (
    <div>
      <PageHeader
        title="Analytics"
        subtitle="Continuity-of-care metrics across your oncology panel."
      />

      <div className="mb-5 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {kpis.map(([k, v]) => (
          <div key={k as string} className="card p-4">
            <div className="text-[11px] uppercase tracking-wider text-ink-400">{k}</div>
            <div className="mt-1 text-2xl font-bold text-ink-900">{v ?? "-"}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <div className="card p-5">
          <h2 className="mb-4 text-sm font-semibold text-ink-900">
            Follow-ups completed / month
          </h2>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={trend}>
                <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#8a93a3" }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#8a93a3" }} width={28} />
                <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid rgba(0,0,0,0.06)", fontSize: 12 }} />
                <Bar dataKey="completed" radius={[6, 6, 0, 0]}>
                  {trend.map((_, i) => (
                    <Cell key={i} fill={i === trend.length - 1 ? "#635bff" : "#c6ccff"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card p-5">
          <h2 className="mb-4 text-sm font-semibold text-ink-900">Risk distribution</h2>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={riskCounts} layout="vertical">
                <XAxis type="number" hide />
                <YAxis dataKey="risk" type="category" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "#5b6472" }} width={60} />
                <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid rgba(0,0,0,0.06)", fontSize: 12 }} />
                <Bar dataKey="count" radius={[0, 6, 6, 0]}>
                  {riskCounts.map((r) => (
                    <Cell key={r.risk} fill={riskColors[r.risk]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
