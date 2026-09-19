import React, { useEffect, useState } from "react";
import {
  Activity,
  CheckCircle2,
  GitBranch,
  LayoutDashboard,
  Users,
  XCircle,
} from "lucide-react";
import { api } from "./services/api";
import GraphView from "./components/GraphView";

const TABS = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "students", label: "Students", icon: Users },
  { id: "graph", label: "Knowledge graph", icon: GitBranch },
  { id: "match", label: "Match & approval", icon: CheckCircle2 },
  { id: "runs", label: "Run monitor", icon: Activity },
];

function Stat({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">{value}</div>
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState("dashboard");
  const [overview, setOverview] = useState(null);
  const [students, setStudents] = useState([]);
  const [profiles, setProfiles] = useState({});
  const [graph, setGraph] = useState(null);
  const [match, setMatch] = useState(null);
  const [session, setSession] = useState(null);
  const [history, setHistory] = useState([]);
  const [filterConcept, setFilterConcept] = useState("");
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    try {
      const [o, s, p, g] = await Promise.all([
        api.overview(),
        api.students(),
        api.profiles(),
        api.graph(),
      ]);
      setOverview(o);
      setStudents(s);
      setProfiles(p);
      setGraph(g);
      try {
        const m = await api.currentMatch();
        setMatch(m);
        setHistory(await api.runHistory(m.run_id));
      } catch {
        setMatch(null);
      }
    } catch (e) {
      setError(String(e.message));
    }
  };

  useEffect(() => {
    load();
  }, []);

  const decide = async (fn) => {
    if (!match) return;
    await fn(match.id);
    await load();
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-6 py-5">
          <h1 className="text-xl font-semibold">ConceptBridge</h1>
          <p className="text-sm text-slate-500">From concept gaps to complementary connections</p>
        </div>
      </header>

      <div className="mx-auto flex max-w-6xl gap-6 px-6 py-6">
        <nav className="w-52 shrink-0 space-y-1">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm ${
                tab === id ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-200"
              }`}
            >
              <Icon size={16} /> {label}
            </button>
          ))}
          <button
            onClick={load}
            className="mt-4 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            Refresh
          </button>
        </nav>

        <main className="flex-1 space-y-4">
          {error && (
            <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
              {error} — is the backend running on port 8000?
            </div>
          )}

          {tab === "dashboard" && overview && (
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <Stat label="Students" value={overview.students} />
              <Stat label="Active edges" value={overview.active_edges} />
              <Stat label="Matches" value={overview.matches} />
              <Stat label="Sessions" value={overview.sessions} />
              <Stat label="Knowledge cycles" value={overview.graph_health.cycle_count} />
              <Stat label="Bottleneck concepts" value={overview.graph_health.bottleneck_concept_count} />
              <Stat label="Isolated students" value={overview.graph_health.isolated_student_count} />
              <Stat label="Avg learning gain" value={overview.average_learning_gain} />
            </div>
          )}

          {tab === "students" && (
            <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
              <table className="w-full text-sm">
                <thead className="bg-slate-100 text-left text-xs uppercase text-slate-500">
                  <tr>
                    <th className="p-3">Student</th>
                    <th className="p-3">Concept scores</th>
                  </tr>
                </thead>
                <tbody>
                  {students.map((s) => (
                    <tr key={s.id} className="border-t border-slate-100">
                      <td className="p-3 font-medium">
                        {s.name} <span className="text-slate-400">{s.id}</span>
                      </td>
                      <td className="p-3">
                        <div className="flex flex-wrap gap-1">
                          {Object.entries(profiles[s.id] || {}).map(([c, v]) => (
                            <span
                              key={c}
                              className={`rounded px-2 py-0.5 text-xs ${
                                v >= 0.7
                                  ? "bg-emerald-100 text-emerald-800"
                                  : v < 0.6
                                  ? "bg-amber-100 text-amber-800"
                                  : "bg-slate-100 text-slate-600"
                              }`}
                            >
                              {c} {v.toFixed(2)}
                            </span>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {tab === "graph" && (
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <GraphView graph={graph} filterConcept={filterConcept} onFilter={setFilterConcept} />
            </div>
          )}

          {tab === "match" && (
            <div className="space-y-4">
              {!match && (
                <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
                  No match is waiting for approval. Run matchmaking from the API or the demo script.
                </div>
              )}
              {match && (
                <div className="rounded-xl border border-slate-200 bg-white p-5">
                  <div className="flex items-center justify-between">
                    <h2 className="font-semibold">
                      Group {match.members.join(" · ")}{" "}
                      <span className="text-slate-400">score {match.score}</span>
                    </h2>
                    <span className="rounded-full bg-slate-100 px-3 py-1 text-xs">{match.status}</span>
                  </div>

                  <h3 className="mt-4 text-xs uppercase text-slate-500">Teaching relationships</h3>
                  <ul className="mt-2 space-y-1 text-sm">
                    {match.relationships.map((r, i) => (
                      <li key={i}>
                        <b>{r.teacher}</b> → <b>{r.learner}</b> · {r.concept} · teacher{" "}
                        {r.teacher_score} / learner {r.learner_score} · gap {r.gap}
                      </li>
                    ))}
                  </ul>

                  <h3 className="mt-4 text-xs uppercase text-slate-500">Why this group?</h3>
                  <div className="mt-2 grid grid-cols-2 gap-2 text-sm md:grid-cols-4">
                    {Object.entries(match.components).map(([k, v]) => (
                      <div key={k} className="rounded-lg bg-slate-50 p-2">
                        <div className="text-xs text-slate-500">{k.replace(/_/g, " ")}</div>
                        <div className="font-medium">{v}</div>
                      </div>
                    ))}
                  </div>

                  {match.status === "PROPOSED" && (
                    <div className="mt-5 flex gap-2">
                      <button
                        onClick={() => decide(api.approve)}
                        className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm text-white"
                      >
                        <CheckCircle2 size={16} /> Approve
                      </button>
                      <button
                        onClick={() => decide(api.reject)}
                        className="flex items-center gap-2 rounded-lg bg-slate-200 px-4 py-2 text-sm"
                      >
                        <XCircle size={16} /> Reject
                      </button>
                    </div>
                  )}

                  {match.status === "APPROVED" && (
                    <button
                      onClick={async () => setSession(await api.generateSession(match.id))}
                      className="mt-5 rounded-lg bg-slate-900 px-4 py-2 text-sm text-white"
                    >
                      Generate peer-learning session
                    </button>
                  )}
                </div>
              )}

              {session && (
                <div className="rounded-xl border border-slate-200 bg-white p-5">
                  <h2 className="font-semibold">Session {session.id}</h2>
                  <p className="text-sm text-slate-600">{session.plan.objective}</p>
                  {session.plan.rounds.map((r, i) => (
                    <div key={i} className="mt-3 rounded-lg bg-slate-50 p-3 text-sm">
                      <div className="font-medium">
                        {r.teacher} → {r.learner} · {r.concept}
                      </div>
                      <p className="mt-1 text-slate-600">{r.explanation}</p>
                      <p className="mt-1 text-slate-500">Check: {r.understanding_check}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {tab === "runs" && (
            <div className="rounded-xl border border-slate-200 bg-white p-5">
              <h2 className="font-semibold">State transitions</h2>
              {history.length === 0 && (
                <p className="mt-2 text-sm text-slate-500">No active run loaded.</p>
              )}
              <ol className="mt-3 space-y-2 text-sm">
                {history.map((h, i) => (
                  <li key={i} className="flex gap-3">
                    <span className="w-44 shrink-0 font-mono text-xs text-slate-500">
                      {h.from || "—"} → {h.to}
                    </span>
                    <span className="text-slate-600">{h.reason}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
