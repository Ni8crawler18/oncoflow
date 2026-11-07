"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import PageHeader from "@/components/PageHeader";
import { Icon } from "@/components/icons";
import { api, ImportPreview, ImportResult } from "@/lib/api";

// Header/schema templates only — no fabricated patient data.
const TEMPLATE_CSV = `name,phone,age,sex,diagnosis,stage,regimen,risk,mrn,diagnosed_on\n`;

const TEMPLATE_JSON = `[
  {
    "name": "",
    "phone": "",
    "age": 0,
    "sex": "",
    "diagnosis": "",
    "stage": "",
    "regimen": "",
    "risk": "",
    "mrn": "",
    "diagnosed_on": ""
  }
]`;

export default function IntegratorPage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);

  async function handleFile(f: File) {
    setError("");
    setResult(null);
    setFile(f);
    setBusy(true);
    try {
      setPreview(await api.importPreview(f));
    } catch (e: any) {
      setError(e.message || "Could not read file");
      setPreview(null);
    } finally {
      setBusy(false);
    }
  }

  async function runImport() {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      setResult(await api.importPatients(file));
    } catch (e: any) {
      setError(e.message || "Import failed");
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setFile(null);
    setPreview(null);
    setResult(null);
    setError("");
  }

  function download(name: string, content: string, type: string) {
    const url = URL.createObjectURL(new Blob([content], { type }));
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    URL.revokeObjectURL(url);
  }

  const cols =
    preview && preview.rows.length
      ? preview.rows.reduce<string[]>((acc, r) => {
          Object.keys(r).forEach((k) => {
            if (!acc.includes(k)) acc.push(k);
          });
          return acc;
        }, [])
      : [];

  return (
    <div>
      <PageHeader
        title="Data Integrator"
        subtitle="Import patient records from other HMS / EMR systems into OncoFlow."
      />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        {/* Upload */}
        <div className="lg:col-span-2">
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              const f = e.dataTransfer.files?.[0];
              if (f) handleFile(f);
            }}
            className={`card flex flex-col items-center justify-center p-10 text-center transition ${
              dragging ? "ring-2 ring-brand-400" : ""
            }`}
          >
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-50 text-brand-600">
              <Icon.upload width={26} height={26} />
            </div>
            <div className="mt-4 text-sm font-medium text-ink-900">
              Drag &amp; drop a file here
            </div>
            <div className="mt-1 text-xs text-ink-400">
              CSV, TSV, JSON array, or FHIR R4 Bundle
            </div>
            <button
              onClick={() => inputRef.current?.click()}
              className="mt-4 rounded-xl bg-brand-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-600"
            >
              Choose file
            </button>
            <input
              ref={inputRef}
              type="file"
              accept=".csv,.tsv,.json,.txt"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleFile(f);
              }}
            />
            {file && (
              <div className="mt-4 text-xs text-ink-500">
                Selected: <span className="font-medium">{file.name}</span>
              </div>
            )}
          </div>

          {error && (
            <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-600">
              {error}
            </div>
          )}

          {/* Preview */}
          {preview && !result && (
            <div className="card mt-5 overflow-hidden">
              <div className="flex items-center justify-between border-b border-black/[0.06] px-5 py-3">
                <div className="text-sm font-semibold text-ink-900">
                  Preview · {preview.count} record{preview.count !== 1 ? "s" : ""}{" "}
                  detected
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={reset}
                    className="rounded-lg px-3 py-1.5 text-xs font-medium text-ink-500 hover:bg-black/5"
                  >
                    Clear
                  </button>
                  <button
                    onClick={runImport}
                    disabled={busy}
                    className="rounded-lg bg-brand-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-600 disabled:opacity-60"
                  >
                    {busy ? "Importing…" : `Import ${preview.count} into database`}
                  </button>
                </div>
              </div>
              <div className="max-h-[360px] overflow-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-white">
                    <tr className="text-left text-[11px] uppercase tracking-wider text-ink-400">
                      {cols.map((c) => (
                        <th key={c} className="whitespace-nowrap px-4 py-2 font-semibold">
                          {c}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.map((r, i) => (
                      <tr key={i} className="border-t border-black/[0.04]">
                        {cols.map((c) => (
                          <td key={c} className="whitespace-nowrap px-4 py-2 text-ink-700">
                            {r[c] != null ? String(r[c]) : "-"}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Result */}
          {result && (
            <div className="card mt-5 p-6">
              <div className="flex items-center gap-2 text-sm font-semibold text-emerald-600">
                <Icon.shield width={16} height={16} /> Import complete
              </div>
              <div className="mt-4 grid grid-cols-3 gap-4">
                {[
                  ["Imported", result.imported, "text-emerald-600"],
                  ["Skipped (duplicates)", result.skipped, "text-amber-600"],
                  ["Errors", result.errors.length, "text-rose-600"],
                ].map(([label, val, tint]) => (
                  <div key={label as string} className="rounded-xl bg-ink-900/[0.03] p-4">
                    <div className={`text-2xl font-bold ${tint}`}>{val as number}</div>
                    <div className="text-xs text-ink-500">{label as string}</div>
                  </div>
                ))}
              </div>
              {result.errors.length > 0 && (
                <ul className="mt-4 list-disc space-y-1 pl-5 text-xs text-rose-600">
                  {result.errors.slice(0, 10).map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
              )}
              <div className="mt-5 flex gap-2">
                <Link
                  href="/patients"
                  className="rounded-xl bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600"
                >
                  View patients
                </Link>
                <button
                  onClick={reset}
                  className="rounded-xl border border-black/10 px-4 py-2 text-sm font-medium text-ink-600 hover:bg-black/5"
                >
                  Import another file
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Side info */}
        <div className="space-y-5">
          <div className="card p-5">
            <div className="mb-3 text-sm font-semibold text-ink-900">
              Supported formats
            </div>
            <ul className="space-y-2 text-sm text-ink-600">
              {[
                ["CSV / TSV", "Header row with column names"],
                ["JSON", "Array of patient objects"],
                ["FHIR R4", "Bundle of Patient resources"],
              ].map(([a, b]) => (
                <li key={a} className="flex items-start gap-2">
                  <Icon.database width={15} height={15} className="mt-0.5 text-brand-500" />
                  <span>
                    <span className="font-medium text-ink-800">{a}</span>
                    <span className="block text-xs text-ink-400">{b}</span>
                  </span>
                </li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-ink-400">
              Column names are matched flexibly (e.g. diagnosis, gender, mobile).
              Duplicate phone / MRN records are skipped automatically.
            </p>
          </div>

          <div className="card p-5">
            <div className="mb-3 text-sm font-semibold text-ink-900">Templates</div>
            <div className="space-y-2">
              <button
                onClick={() => download("oncoflow-template.csv", TEMPLATE_CSV, "text/csv")}
                className="flex w-full items-center justify-between rounded-xl border border-black/10 px-3 py-2 text-sm text-ink-700 hover:bg-black/5"
              >
                CSV template <Icon.upload width={15} height={15} className="rotate-180" />
              </button>
              <button
                onClick={() => download("oncoflow-template.json", TEMPLATE_JSON, "application/json")}
                className="flex w-full items-center justify-between rounded-xl border border-black/10 px-3 py-2 text-sm text-ink-700 hover:bg-black/5"
              >
                JSON template <Icon.upload width={15} height={15} className="rotate-180" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
