import { useEffect, useState } from "react";

import { HealthStatus } from "../components/HealthStatus";
import { EvidenceUpload } from "../components/EvidenceUpload";
import { getHealth } from "../services/api";

type ConnectionState = "loading" | "online" | "offline";

export function LandingPage() {
  const [connectionState, setConnectionState] = useState<ConnectionState>("loading");

  useEffect(() => {
    let active = true;

    getHealth()
      .then(() => active && setConnectionState("online"))
      .catch(() => active && setConnectionState("offline"));

    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-16">
      <section className="w-full max-w-3xl rounded-3xl border border-slate-800 bg-slate-900/70 p-8 shadow-2xl shadow-cyan-950/20 sm:p-14">
        <div className="mb-10 flex items-center justify-between gap-4">
          <span className="text-lg font-semibold tracking-tight text-white">ProofMesh</span>
          <HealthStatus state={connectionState} />
        </div>
        <p className="mb-4 text-sm font-semibold uppercase tracking-[0.2em] text-cyan-400">
          Digital evidence integrity
        </p>
        <h1 className="max-w-2xl text-4xl font-bold tracking-tight text-white sm:text-6xl">
          Evidence you can trace and trust.
        </h1>
        <p className="mt-6 max-w-xl text-lg leading-8 text-slate-300">
          Start an investigation by securely preserving a local copy of your evidence and its SHA-256 fingerprint.
        </p>
        <EvidenceUpload />
      </section>
    </main>
  );
}
