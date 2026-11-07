import React from "react";

export function riskPill(risk: string) {
  const map: Record<string, string> = {
    high: "bg-rose-50 text-rose-600",
    medium: "bg-amber-50 text-amber-600",
    low: "bg-emerald-50 text-emerald-600",
  };
  return (
    <span className={`pill ${map[risk] || "bg-gray-100 text-gray-600"}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {risk[0].toUpperCase() + risk.slice(1)} risk
    </span>
  );
}

export function statusPill(status: string) {
  const map: Record<string, string> = {
    scheduled: "bg-brand-50 text-brand-600",
    completed: "bg-emerald-50 text-emerald-600",
    missed: "bg-rose-50 text-rose-600",
    overdue: "bg-amber-50 text-amber-600",
  };
  return (
    <span className={`pill ${map[status] || "bg-gray-100 text-gray-600"}`}>
      {status[0].toUpperCase() + status.slice(1)}
    </span>
  );
}

export function categoryPill(cat: string) {
  const map: Record<string, string> = {
    symptom: "bg-rose-50 text-rose-600",
    feedback: "bg-brand-50 text-brand-600",
    general: "bg-gray-100 text-gray-500",
  };
  return <span className={`pill ${map[cat] || "bg-gray-100"}`}>{cat}</span>;
}

export function initials(name: string) {
  return name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function Avatar({ name }: { name: string }) {
  const hues = [210, 260, 330, 20, 150, 290];
  const hue = hues[name.charCodeAt(0) % hues.length];
  return (
    <div
      className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white"
      style={{ background: `hsl(${hue} 60% 55%)` }}
    >
      {initials(name)}
    </div>
  );
}

export function timeAgo(iso: string) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} h ago`;
  return `${Math.floor(diff / 86400)} d ago`;
}

export function formatTime(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
