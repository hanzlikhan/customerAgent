import { useRef, useState } from "react";
import {
  Camera,
  CheckCircle2,
  ChevronDown,
  CircleAlert,
  Download,
  FileSpreadsheet,
  Loader2,
  Package,
  Upload,
} from "lucide-react";
import { api } from "../lib/api";

const TEMPLATE_URL =
  "https://github.com/hanzlikhan/customerAgent/raw/main/data/catalog_template.xlsx";

const STEPS = [
  {
    n: 1,
    title: "Prepare your list",
    text: "Download the template and fill in your products — or snap a photo of your printed rate list. Printed lists only; handwriting is not reliably readable.",
  },
  {
    n: 2,
    title: "Upload and review",
    text: "Upload the file below and check the parsed preview. Rows with problems are flagged, never silently imported.",
  },
  {
    n: 3,
    title: "Import",
    text: "Click Import. The catalog is indexed immediately and the AI starts answering from it.",
  },
];

export default function Catalog() {
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [preview, setPreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [showRawOcr, setShowRawOcr] = useState(false);
  const inputRef = useRef(null);

  function reset() {
    setFile(null);
    setPreview(null);
    setResult(null);
    setError(null);
    setShowRawOcr(false);
    if (inputRef.current) inputRef.current.value = "";
  }

  async function handleUpload(f) {
    const target = f ?? file;
    if (!target) return;
    setUploading(true);
    setError(null);
    setResult(null);
    try {
      const data = await api.uploadCatalog(target);
      setPreview(data);
    } catch (e) {
      setError(e.message);
      setPreview(null);
    } finally {
      setUploading(false);
    }
  }

  async function handleImport() {
    if (!preview?.rows?.length) return;
    setImporting(true);
    setError(null);
    try {
      const data = await api.importCatalog(preview.rows, preview.filename);
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setImporting(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Catalog onboarding</h2>
        <p className="text-sm text-slate-500">
          Get any shop&apos;s price list into DukaanAI in minutes.
        </p>
      </div>

      {/* Steps */}
      <div className="grid gap-3 md:grid-cols-3">
        {STEPS.map((s) => (
          <div
            key={s.n}
            className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-700 text-sm font-bold text-white">
              {s.n}
            </div>
            <div className="mt-2 font-semibold text-slate-900">{s.title}</div>
            <p className="mt-1 text-sm leading-relaxed text-slate-500">
              {s.text}
            </p>
          </div>
        ))}
      </div>

      <a
        href={TEMPLATE_URL}
        target="_blank"
        rel="noreferrer"
        className="flex w-fit items-center gap-2 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 hover:border-emerald-500 hover:text-emerald-700"
      >
        <Download className="h-4 w-4" />
        Download spreadsheet template
      </a>

      {/* Dropzone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const f = e.dataTransfer.files?.[0];
          if (f) {
            setFile(f);
            setPreview(null);
            setResult(null);
          }
        }}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-4 py-10 text-center transition-colors ${
          dragOver
            ? "border-emerald-500 bg-emerald-50"
            : "border-slate-300 bg-white hover:border-emerald-400"
        }`}
      >
        <div className="flex gap-3 text-slate-400">
          <FileSpreadsheet className="h-8 w-8" />
          <Camera className="h-8 w-8" />
        </div>
        <p className="mt-3 text-sm font-medium text-slate-700">
          {file ? file.name : "Drop a catalog file here, or click to browse"}
        </p>
        <p className="mt-1 text-xs text-slate-400">
          .xlsx / .csv spreadsheet, or .png / .jpg photo of a printed rate list
        </p>
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.csv,.png,.jpg,.jpeg"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) {
              setFile(f);
              setPreview(null);
              setResult(null);
            }
          }}
        />
      </div>

      {file && !preview && (
        <div>
          <button
            onClick={() => handleUpload()}
            disabled={uploading}
            className="flex items-center gap-2 rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-medium text-white hover:bg-emerald-800 disabled:opacity-50"
          >
            {uploading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            {uploading ? "Reading file…" : "Upload and preview"}
          </button>
        </div>
      )}

      {error && (
        <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />
          <span className="whitespace-pre-line">{error}</span>
        </div>
      )}

      {/* Preview */}
      {preview && (
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div className="font-semibold text-slate-900">
              Preview — {preview.filename}
            </div>
            <button
              onClick={reset}
              className="text-sm font-medium text-slate-500 hover:text-slate-800"
            >
              Choose another file
            </button>
          </div>

          {preview.raw_text != null && (
            <div className="mb-3">
              <button
                onClick={() => setShowRawOcr((s) => !s)}
                className="flex items-center gap-1 text-sm font-medium text-slate-600 hover:text-slate-900"
              >
                What the OCR actually read
                <ChevronDown
                  className={`h-4 w-4 transition-transform ${
                    showRawOcr ? "rotate-180" : ""
                  }`}
                />
              </button>
              {showRawOcr && (
                <pre className="mt-2 max-h-40 overflow-auto rounded-lg bg-slate-50 p-3 text-xs leading-relaxed text-slate-600">
                  {preview.raw_text || "(nothing readable)"}
                </pre>
              )}
            </div>
          )}

          {preview.rows?.length > 0 ? (
            <>
              <p className="mb-2 text-sm text-slate-600">
                <span className="font-semibold text-slate-900">
                  {preview.rows.length} valid items
                </span>{" "}
                ready to import
                {preview.rows.length > 50 && " (showing first 50)"}:
              </p>
              <div className="scroll-slim max-h-80 overflow-auto rounded-xl border border-slate-200">
                <table className="w-full min-w-[560px] text-sm">
                  <thead className="sticky top-0 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-3 py-2 font-semibold">Name (EN)</th>
                      <th className="px-3 py-2 font-semibold">Name (Roman Urdu)</th>
                      <th className="px-3 py-2 text-right font-semibold">Price</th>
                      <th className="px-3 py-2 font-semibold">Unit</th>
                      <th className="px-3 py-2 font-semibold">Category</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {preview.rows.slice(0, 50).map((r, i) => (
                      <tr key={i} className="text-slate-700">
                        <td className="px-3 py-2">{r.name_en}</td>
                        <td className="px-3 py-2">{r.name_ur_roman}</td>
                        <td className="px-3 py-2 text-right font-medium">
                          {r.price.toLocaleString()}
                        </td>
                        <td className="px-3 py-2">{r.unit}</td>
                        <td className="px-3 py-2">{r.category || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <p className="text-sm text-slate-500">
              No valid rows found in this file.
            </p>
          )}

          {preview.errors?.length > 0 && (
            <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
              <p className="text-sm font-medium text-amber-800">
                {preview.errors.length} row(s) have problems and will be
                skipped:
              </p>
              <ul className="mt-1.5 list-inside list-disc text-sm text-amber-700">
                {preview.errors.map((e, i) => (
                  <li key={i}>{e.reason}</li>
                ))}
              </ul>
            </div>
          )}

          {preview.rows?.length > 0 && !result && (
            <button
              onClick={handleImport}
              disabled={importing}
              className="mt-4 flex items-center gap-2 rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-medium text-white hover:bg-emerald-800 disabled:opacity-50"
            >
              {importing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Package className="h-4 w-4" />
              )}
              {importing
                ? "Importing…"
                : `Import ${preview.rows.length} items`}
            </button>
          )}

          {result && (
            <div className="mt-4 flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
              <CheckCircle2 className="mt-0.5 h-4.5 w-4.5 shrink-0" />
              <div>
                <span className="font-semibold">
                  Imported {result.imported} items
                </span>{" "}
                — index rebuilt. The AI can answer from them right away.
                {result.errors?.length > 0 && (
                  <span>
                    {" "}
                    {result.errors.length} row(s) were rejected on
                    re-validation.
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
