"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Icon } from "./icons";
import { logout, getUser, AuthUser } from "@/lib/auth";
import { initials } from "@/lib/ui";

const groups = [
  {
    label: "Overview",
    items: [
      { href: "/", label: "Home", icon: Icon.home },
      { href: "/patients", label: "Patients", icon: Icon.users },
    ],
  },
  {
    label: "Care coordination",
    items: [
      { href: "/appointments", label: "Appointments", icon: Icon.calendar },
      { href: "/schedule", label: "Follow-ups & Scheduling", icon: Icon.bolt },
      { href: "/messages", label: "Telegram Inbox", icon: Icon.chat },
    ],
  },
  {
    label: "Oncology",
    items: [
      { href: "/oncology/treatment", label: "Treatment Tracker", icon: Icon.flask },
      { href: "/oncology/imaging", label: "Imaging & Restaging", icon: Icon.scan },
      { href: "/oncology/safety", label: "Safety & Toxicity", icon: Icon.shield },
    ],
  },
  {
    label: "Admin",
    items: [
      { href: "/analytics", label: "Analytics", icon: Icon.chart },
      { href: "/integrator", label: "Data Integrator", icon: Icon.database },
    ],
  },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    setUser(getUser());
  }, []);

  return (
    <aside className="flex h-full w-[248px] shrink-0 flex-col border-r border-black/[0.06] bg-[#fbfbfc]">
      <div className="px-5 pb-3 pt-6">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/logo-mark.png"
          alt="Oncoflow"
          className="h-[22px] w-auto object-contain object-left"
          style={{ filter: "hue-rotate(212deg) saturate(1.25)" }}
        />
        <div className="mt-2 text-[11px] text-ink-400">Oncology follow-up portal</div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 pb-4">
        {groups.map((g) => (
          <div key={g.label}>
            <div className="nav-label">{g.label}</div>
            {g.items.map((it) => {
              const active =
                it.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(it.href);
              const I = it.icon;
              return (
                <Link
                  key={it.href}
                  href={it.href}
                  className={`nav-item ${active ? "nav-item-active" : ""}`}
                >
                  <I width={18} height={18} stroke={active ? "white" : "currentColor"} />
                  {it.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="border-t border-black/[0.06] p-3">
        <div className="flex items-center gap-3 rounded-xl px-2 py-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-100 text-sm font-semibold text-brand-700">
            {user ? initials(user.name) : "-"}
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium text-ink-900">
              {user?.name || "-"}
            </div>
            <div className="truncate text-[11px] text-ink-400">
              {user?.specialty || ""}
            </div>
          </div>
          <button
            onClick={() => {
              logout();
              router.push("/login");
            }}
            className="text-[11px] font-medium text-ink-400 hover:text-ink-700"
          >
            Sign out
          </button>
        </div>
      </div>
    </aside>
  );
}
