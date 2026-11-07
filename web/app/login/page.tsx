"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@/components/icons";
import { login, register } from "@/lib/auth";

type Mode = "login" | "register";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [name, setName] = useState("");
  const [specialty, setSpecialty] = useState("Medical Oncology");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(name, email, password, specialty);
      }
      router.push("/");
    } catch (err: any) {
      setError(err.message || "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  const inputCls =
    "w-full rounded-xl border border-black/10 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100";

  return (
    <div className="flex min-h-screen bg-canvas">
      {/* Left: brand panel (same theme as dashboard) */}
      <div className="relative hidden w-1/2 flex-col justify-center overflow-hidden bg-gradient-to-br from-brand-600 via-brand-600 to-brand-800 p-12 text-white lg:flex">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/logo-mark.png"
          alt="Oncoflow"
          className="mb-10 h-8 w-auto object-contain object-left brightness-0 invert"
        />
        <div>
          <h1 className="text-[40px] font-semibold leading-[1.1] tracking-tight">
            Keep every oncology patient connected to care.
          </h1>
          <p className="mt-4 max-w-md text-white/70">
            Early identification of patients needing follow-up, Telegram engagement,
            and conflict-free scheduling, in one premium workspace for care teams.
          </p>
          <div className="mt-9 grid grid-cols-3 gap-6">
            {[
              ["35%", "fewer missed follow-ups"],
              ["Telegram", "patient engagement"],
              ["0 clashes", "smart scheduling"],
            ].map(([a, b]) => (
              <div key={b}>
                <div className="text-2xl font-semibold">{a}</div>
                <div className="text-xs text-white/60">{b}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-white/10 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 -left-20 h-96 w-96 rounded-full bg-brand-400/20 blur-3xl" />
      </div>

      {/* Right: form */}
      <div className="flex flex-1 items-center justify-center p-6">
        <div className="card w-full max-w-sm p-8">
          {/* Mobile logo */}
          <div className="mb-6 lg:hidden">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/logo-mark.png"
              alt="Oncoflow"
              className="h-7 w-auto"
              style={{ filter: "hue-rotate(212deg) saturate(1.25)" }}
            />
          </div>

          <div className="mb-6">
            <h2 className="text-xl font-semibold text-ink-900">
              {mode === "login" ? "Welcome back" : "Create your account"}
            </h2>
            <p className="mt-1 text-sm text-ink-500">
              {mode === "login"
                ? "Sign in to the OncoFlow care portal."
                : "Register as a clinician to start managing follow-ups."}
            </p>
          </div>

          {/* Tabs */}
          <div className="mb-5 flex gap-1 rounded-xl bg-black/[0.04] p-1">
            {(["login", "register"] as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => {
                  setMode(m);
                  setError("");
                }}
                className={`flex-1 rounded-lg py-1.5 text-sm font-medium capitalize transition ${
                  mode === m ? "bg-white text-ink-900 shadow-soft" : "text-ink-500"
                }`}
              >
                {m === "login" ? "Sign in" : "Register"}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="space-y-4">
            {mode === "register" && (
              <>
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-ink-700">
                    Full name
                  </label>
                  <input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Dr. Jane Doe"
                    className={inputCls}
                    required
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-ink-700">
                    Specialty
                  </label>
                  <input
                    value={specialty}
                    onChange={(e) => setSpecialty(e.target.value)}
                    className={inputCls}
                  />
                </div>
              </>
            )}
            <div>
              <label className="mb-1.5 block text-sm font-medium text-ink-700">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@oncoflow.health"
                className={inputCls}
                required
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-ink-700">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className={inputCls}
                required
              />
            </div>
            {error && <p className="text-sm text-rose-600">{error}</p>}
            <button
              type="submit"
              disabled={busy}
              className="w-full rounded-xl bg-brand-500 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-600 disabled:opacity-60"
            >
              {busy
                ? "Please wait…"
                : mode === "login"
                ? "Sign in"
                : "Create account"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
