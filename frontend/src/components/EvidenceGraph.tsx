import { useMemo } from "react";
import type { EvidenceGraphResponse } from "../types/graph";

interface EvidenceGraphProps {
  graph: EvidenceGraphResponse;
}

interface LayoutNode {
  id: string;
  x: number;
  y: number;
  node_type: string;
  label: string;
}

const NODE_COLORS: Record<string, string> = {
  Artifact: "#22d3ee",
  Metadata: "#a78bfa",
  Timestamp: "#f472b6",
  "Image Signal": "#34d399",
  "Suspicious Region": "#f87171",
  "OCR Text": "#60a5fa",
  "Document Signal": "#fbbf24",
  Finding: "#f97316",
};

export function EvidenceGraph({ graph }: EvidenceGraphProps) {
  const layout = useMemo(() => computeLayout(graph.nodes, graph.edges), [graph]);

  const width = 800;
  const height = 600;

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
      <h2 className="text-lg font-semibold text-white">Evidence Graph</h2>
      <p className="mt-1 text-xs text-slate-400">
        {graph.nodes.length} nodes · {graph.edges.length} relationships
      </p>
      <div className="mt-4 overflow-x-auto">
        <svg viewBox={`0 0 ${width} ${height}`} className="h-[600px] w-full max-w-4xl">
          {graph.edges.map((edge, index) => {
            const source = layout.get(edge.source);
            const target = layout.get(edge.target);
            if (!source || !target) return null;
            return (
              <line
                key={index}
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                stroke="#475569"
                strokeWidth="1.5"
              />
            );
          })}
          {graph.nodes.map((node) => {
            const pos = layout.get(node.id);
            if (!pos) return null;
            const color = NODE_COLORS[node.node_type] ?? "#94a3b8";
            const label = node.label.length > 18 ? node.label.slice(0, 18) + "…" : node.label;
            return (
              <g key={node.id}>
                <circle cx={pos.x} cy={pos.y} r="8" fill={color} />
                <text x={pos.x} y={pos.y + 20} textAnchor="middle" className="fill-slate-300 text-[10px]">
                  {label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </section>
  );
}

function computeLayout(
  nodes: { id: string; node_type: string; label: string }[],
  edges: { source: string; target: string; relationship: string }[]
): Map<string, { x: number; y: number }> {
  const positions = new Map<string, { x: number; y: number }>();
  const centerX = 400;
  const centerY = 300;
  const radius = 220;

  nodes.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / nodes.length;
    positions.set(node.id, {
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    });
  });

  for (let iter = 0; iter < 120; iter++) {
    const repulsion = 900;
    const attraction = 0.004;
    const centerGravity = 0.015;
    const forces = new Map<string, { x: number; y: number }>();
    nodes.forEach((n) => forces.set(n.id, { x: 0, y: 0 }));

    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = positions.get(nodes[i].id)!;
        const b = positions.get(nodes[j].id)!;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = repulsion / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        forces.get(nodes[i].id)!.x -= fx;
        forces.get(nodes[i].id)!.y -= fy;
        forces.get(nodes[j].id)!.x += fx;
        forces.get(nodes[j].id)!.y += fy;
      }
    }

    for (const edge of edges) {
      const a = positions.get(edge.source);
      const b = positions.get(edge.target);
      if (!a || !b) continue;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const force = (dist - 80) * attraction;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      forces.get(edge.source)!.x += fx;
      forces.get(edge.source)!.y += fy;
      forces.get(edge.target)!.x -= fx;
      forces.get(edge.target)!.y -= fy;
    }

    for (const node of nodes) {
      const pos = positions.get(node.id)!;
      const f = forces.get(node.id)!;
      pos.x += f.x + (centerX - pos.x) * centerGravity;
      pos.y += f.y + (centerY - pos.y) * centerGravity;
    }
  }

  return positions;
}
