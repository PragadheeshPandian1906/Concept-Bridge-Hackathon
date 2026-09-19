import React from "react";

/** Circular layout of the current knowledge-transfer graph. */
export default function GraphView({ graph, filterConcept, onFilter }) {
  if (!graph) return null;
  const nodes = graph.nodes || [];
  const size = 520;
  const r = 200;
  const center = size / 2;
  const pos = {};
  nodes.forEach((n, i) => {
    const a = (2 * Math.PI * i) / Math.max(1, nodes.length) - Math.PI / 2;
    pos[n.id] = { x: center + r * Math.cos(a), y: center + r * Math.sin(a) };
  });

  const concepts = [
    ...new Set(graph.edges.flatMap((e) => e.concepts.map((c) => c.concept_id))),
  ];
  const cycleMembers = new Set((graph.cycles || []).flat());
  const reciprocal = new Set(
    (graph.reciprocal || []).flatMap((p) => p.students.map((s) => s))
  );

  const edges = graph.edges.filter(
    (e) => !filterConcept || e.concepts.some((c) => c.concept_id === filterConcept)
  );

  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-2">
        <button
          onClick={() => onFilter("")}
          className={`rounded-full px-3 py-1 text-xs ${!filterConcept ? "bg-slate-900 text-white" : "bg-slate-200"}`}
        >
          all concepts
        </button>
        {concepts.map((c) => (
          <button
            key={c}
            onClick={() => onFilter(c)}
            className={`rounded-full px-3 py-1 text-xs ${filterConcept === c ? "bg-slate-900 text-white" : "bg-slate-200"}`}
          >
            {c}
          </button>
        ))}
      </div>
      <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-2xl">
        <defs>
          <marker id="arrow" markerWidth="10" markerHeight="10" refX="22" refY="3" orient="auto">
            <path d="M0,0 L0,6 L9,3 z" fill="#64748b" />
          </marker>
        </defs>
        {edges.map((e, i) => {
          const a = pos[e.source];
          const b = pos[e.target];
          if (!a || !b) return null;
          return (
            <line
              key={i}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke="#94a3b8"
              strokeWidth={1 + e.edge_score * 2}
              markerEnd="url(#arrow)"
              opacity="0.7"
            />
          );
        })}
        {nodes.map((n) => {
          const p = pos[n.id];
          const isolated = (graph.isolated || []).includes(n.id);
          const fill = isolated ? "#e2e8f0" : cycleMembers.has(n.id) ? "#6366f1" : "#0f172a";
          return (
            <g key={n.id}>
              <circle cx={p.x} cy={p.y} r="18" fill={fill} />
              <text x={p.x} y={p.y + 4} textAnchor="middle" fontSize="9" fill="white">
                {n.id.replace("S00", "S")}
              </text>
              <text x={p.x} y={p.y + 32} textAnchor="middle" fontSize="10" fill="#334155">
                {n.name}
              </text>
            </g>
          );
        })}
      </svg>
      <p className="mt-2 text-xs text-slate-500">
        Dark = student, indigo = part of a knowledge cycle, grey = isolated. Arrow direction is
        teacher → learner; thickness is the transfer gap. Reciprocal pairs:{" "}
        {[...reciprocal].join(", ") || "none"}.
      </p>
    </div>
  );
}
