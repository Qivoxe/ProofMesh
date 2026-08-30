import { ChangeEvent, DragEvent, useRef, useState } from "react";

import { formatBytes } from "../lib/format";

const ACCEPTED_FILE_TYPES = ["image/png", "image/jpeg", "application/pdf"];

interface EvidenceUploadProps {
  onUpload: (file: File) => void;
}

export function EvidenceUpload({ onUpload }: EvidenceUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  function chooseFile(file: File | undefined) {
    if (!file) return;
    setSelectedFile(file);
    setError(null);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    chooseFile(event.dataTransfer.files[0]);
  }

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    chooseFile(event.target.files?.[0]);
  }

  async function handleUpload() {
    if (!selectedFile) return;
    setIsUploading(true);
    setError(null);
    try {
      onUpload(selectedFile);
      setSelectedFile(null);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Unable to upload evidence.");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="mt-10 rounded-2xl border border-slate-700 bg-slate-950/60 p-5 sm:p-6">
      <div
        className="cursor-pointer rounded-xl border border-dashed border-slate-600 px-5 py-8 text-center transition hover:border-cyan-400 hover:bg-cyan-400/5"
        onClick={() => inputRef.current?.click()}
        onDragOver={(event) => event.preventDefault()}
        onDrop={handleDrop}
        role="button"
        tabIndex={0}
        onKeyDown={(event) => event.key === "Enter" && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          className="hidden"
          type="file"
          accept=".png,.jpg,.jpeg,.pdf"
          onChange={handleChange}
        />
        <p className="font-medium text-white">Drop evidence here, or select a file</p>
        <p className="mt-2 text-sm text-slate-400">PNG, JPG, JPEG, or PDF · maximum 50 MB</p>
      </div>

      {selectedFile && (
        <div className="mt-4 flex flex-col gap-3 rounded-xl bg-slate-900 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <p className="truncate font-medium text-slate-100">{selectedFile.name}</p>
            <p className="mt-1 text-sm text-slate-400">{formatBytes(selectedFile.size)} · {selectedFile.type || "Unknown type"}</p>
          </div>
          <button
            className="rounded-lg bg-cyan-400 px-4 py-2 font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
            type="button"
            disabled={isUploading || !ACCEPTED_FILE_TYPES.includes(selectedFile.type)}
            onClick={handleUpload}
          >
            {isUploading ? "Uploading…" : "Upload evidence"}
          </button>
        </div>
      )}

      {selectedFile && !ACCEPTED_FILE_TYPES.includes(selectedFile.type) && (
        <p className="mt-3 text-sm text-rose-300">Select a PNG, JPG, JPEG, or PDF file.</p>
      )}
      {error && <p className="mt-3 text-sm text-rose-300">{error}</p>}
    </div>
  );
}
