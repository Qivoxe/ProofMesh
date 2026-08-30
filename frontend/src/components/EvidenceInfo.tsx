interface EvidenceInfoProps {
  response: {
    filename: string;
    file_type: string;
    file_size: number;
    sha256: string;
  };
}

export function EvidenceInfo({ response }: EvidenceInfoProps) {
  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
      <h2 className="text-lg font-semibold text-white">Evidence</h2>
      <dl className="mt-4 grid gap-3 text-sm text-slate-300 sm:grid-cols-2">
        <div>
          <dt className="text-slate-500">Filename</dt>
          <dd className="mt-1 break-all font-medium text-slate-100">{response.filename}</dd>
        </div>
        <div>
          <dt className="text-slate-500">File type</dt>
          <dd className="mt-1 font-medium text-slate-100">{response.file_type}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Size</dt>
          <dd className="mt-1 font-medium text-slate-100">{formatBytes(response.file_size)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">SHA-256</dt>
          <dd className="mt-1 break-all font-mono text-xs text-slate-100">{response.sha256}</dd>
        </div>
      </dl>
    </section>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
