"use client";

import { useState } from "react";
import { api } from "@/lib/api";

const field =
  "w-full rounded-xl border border-black/10 bg-white px-3 py-2.5 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100";
const label = "mb-1.5 block text-xs font-medium text-ink-700";

export default function AddPatientModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState({
    name: "",
    phone: "",
    age: "",
    sex: "Female",
    cancer_type: "",
    stage: "",
    treatment_line: "1st line",
    regimen: "",
    risk: "medium",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function set(k: string, v: string) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!form.name || !form.phone || !form.cancer_type) {
      setError("Name, phone and diagnosis are required.");
      return;
    }
    setBusy(true);
    try {
      await api.createPatient({
        name: form.name,
        phone: form.phone,
        age: Number(form.age) || 0,
        sex: form.sex,
        cancer_type: form.cancer_type,
        stage: form.stage || "-",
        treatment_line: form.treatment_line,
        regimen: form.regimen,
        risk: form.risk,
      });
      onCreated();
      onClose();
    } catch (err: any) {
      setError(err.message || "Could not create patient");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/30 p-4"
      onClick={onClose}
    >
      <div
        className="card w-full max-w-lg p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-ink-900">New patient</h2>
          <button onClick={onClose} className="text-ink-400 hover:text-ink-700">
            ✕
          </button>
        </div>

        <form onSubmit={submit} className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className={label}>Full name *</label>
            <input className={field} value={form.name} onChange={(e) => set("name", e.target.value)} />
          </div>
          <div>
            <label className={label}>Phone (WhatsApp) *</label>
            <input className={field} placeholder="+91…" value={form.phone} onChange={(e) => set("phone", e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={label}>Age</label>
              <input className={field} type="number" value={form.age} onChange={(e) => set("age", e.target.value)} />
            </div>
            <div>
              <label className={label}>Sex</label>
              <select className={field} value={form.sex} onChange={(e) => set("sex", e.target.value)}>
                <option>Female</option>
                <option>Male</option>
                <option>Other</option>
              </select>
            </div>
          </div>
          <div className="col-span-2">
            <label className={label}>Diagnosis *</label>
            <input className={field} placeholder="e.g. Breast carcinoma" value={form.cancer_type} onChange={(e) => set("cancer_type", e.target.value)} />
          </div>
          <div>
            <label className={label}>Stage</label>
            <input className={field} placeholder="e.g. IIB" value={form.stage} onChange={(e) => set("stage", e.target.value)} />
          </div>
          <div>
            <label className={label}>Treatment line</label>
            <select className={field} value={form.treatment_line} onChange={(e) => set("treatment_line", e.target.value)}>
              <option>1st line</option>
              <option>2nd line</option>
              <option>Maintenance</option>
            </select>
          </div>
          <div>
            <label className={label}>Regimen</label>
            <input className={field} placeholder="e.g. FOLFOX" value={form.regimen} onChange={(e) => set("regimen", e.target.value)} />
          </div>
          <div>
            <label className={label}>Risk</label>
            <select className={field} value={form.risk} onChange={(e) => set("risk", e.target.value)}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>

          {error && <p className="col-span-2 text-sm text-rose-600">{error}</p>}

          <div className="col-span-2 mt-2 flex justify-end gap-2">
            <button type="button" onClick={onClose} className="rounded-xl border border-black/10 px-4 py-2 text-sm font-medium text-ink-600 hover:bg-black/5">
              Cancel
            </button>
            <button type="submit" disabled={busy} className="rounded-xl bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-60">
              {busy ? "Saving…" : "Add patient"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
