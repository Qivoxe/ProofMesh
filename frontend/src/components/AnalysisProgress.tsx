const STEPS = [
  "Uploading",
  "Ingesting evidence",
  "Metadata",
  "Image Forensics",
  "Copy-Move",
  "OCR",
  "Document Analysis",
  "Evidence Fusion",
  "Evidence Graph",
];

interface AnalysisProgressProps {
  currentStep: string;
}

export function AnalysisProgress({ currentStep }: AnalysisProgressProps) {
  const currentIndex = STEPS.indexOf(currentStep);

  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      <div className="w-full max-w-xl rounded-2xl border border-slate-700 bg-slate-900/70 p-8 shadow-2xl shadow-cyan-950/20">
        <h2 className="text-lg font-semibold text-white">Analyzing evidence</h2>
        <p className="mt-1 text-sm text-slate-400">ProofMesh is running forensic inspections. This may take a moment.</p>
        <ul className="mt-6 space-y-3">
          {STEPS.map((step, index) => {
            const isActive = index === currentIndex;
            const isComplete = index < currentIndex || (!currentStep && index > 0);
            return (
              <li key={step} className="flex items-center gap-3 text-sm">
                <span
                  className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${
                    isComplete
                      ? "border-emerald-500 bg-emerald-500/20 text-emerald-300"
                      : isActive
                        ? "border-cyan-400 bg-cyan-400/20 text-cyan-300"
                        : "border-slate-600 text-slate-500"
                  }`}
                >
                  {isComplete ? (
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-3 w-3">
                      <path fillRule="evenodd" d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12Zm13.36-1.814a.75.75 0 1 0-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 0 0-1.06 1.06l2.25 2.25a.75.75 0 0 0 1.14-.094l3.75-5.25Z" clipRule="evenodd" />
                    </svg>
                  ) : isActive ? (
                    <svg className="h-3 w-3 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4Z" />
                    </svg>
                  ) : (
                    <span className="h-1.5 w-1.5 rounded-full bg-current" />
                  )}
                </span>
                <span className={isActive ? "text-cyan-300" : isComplete ? "text-slate-300" : "text-slate-500"}>
                  {step}
                </span>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
