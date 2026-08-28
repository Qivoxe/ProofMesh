interface HealthStatusProps {
  state: "loading" | "online" | "offline";
}

const statusCopy = {
  loading: "Checking API…",
  online: "API connected",
  offline: "API unavailable",
} as const;

const statusColor = {
  loading: "bg-amber-400",
  online: "bg-emerald-400",
  offline: "bg-rose-400",
} as const;

export function HealthStatus({ state }: HealthStatusProps) {
  return (
    <div className="flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-300">
      <span className={`h-2 w-2 rounded-full ${statusColor[state]}`} />
      {statusCopy[state]}
    </div>
  );
}
