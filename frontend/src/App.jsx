import { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { getGraph, getCases, getCase, getReport, getPipeline } from "./api";
import LoginPage from "./LoginPage";

// Entity type color theme (Modern Cyber-Fintech Palette)
const TYPE_CONFIG = {
  customer: { color: "#2563eb", bg: "bg-blue-500", text: "text-blue-700", border: "border-blue-200", label: "Customer", icon: "👤" },
  account: { color: "#0d9488", bg: "bg-teal-600", text: "text-teal-700", border: "border-teal-200", label: "Account", icon: "💳" },
  device: { color: "#d97706", bg: "bg-amber-600", text: "text-amber-700", border: "border-amber-200", label: "Device", icon: "📱" },
  ip: { color: "#9333ea", bg: "bg-purple-600", text: "text-purple-700", border: "border-purple-200", label: "IP Address", icon: "🌐" },
  merchant: { color: "#475569", bg: "bg-slate-600", text: "text-slate-700", border: "border-slate-200", label: "Merchant", icon: "🏪" },
  beneficiary: { color: "#ea580c", bg: "bg-orange-600", text: "text-orange-700", border: "border-orange-200", label: "Beneficiary", icon: "🎯" },
};

const SEV_CONFIG = {
  critical: { bg: "bg-rose-100 text-rose-800 border-rose-300", badge: "bg-rose-600 text-white", border: "border-rose-500", dot: "bg-rose-500" },
  high: { bg: "bg-amber-100 text-amber-800 border-amber-300", badge: "bg-amber-600 text-white", border: "border-amber-500", dot: "bg-amber-500" },
  medium: { bg: "bg-yellow-100 text-yellow-800 border-yellow-300", badge: "bg-yellow-600 text-white", border: "border-yellow-500", dot: "bg-yellow-500" },
  low: { bg: "bg-slate-100 text-slate-700 border-slate-300", badge: "bg-slate-500 text-white", border: "border-slate-400", dot: "bg-slate-400" },
};

export default function App() {
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem("fincrime_user");
      return saved ? JSON.parse(saved) : null;
    } catch (_) {
      return null;
    }
  });

  const [graph, setGraph] = useState(null);
  const [cases, setCases] = useState([]);
  const [pipeline, setPipeline] = useState(null);
  const [active, setActive] = useState(null); // active case id
  const [evidence, setEvidence] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [picked, setPicked] = useState(null); // highlighted entity
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [showLabels, setShowLabels] = useState(true);
  const [filterType, setFilterType] = useState("all");
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [activeTab, setActiveTab] = useState("overview"); // overview | dossier | ledger
  const fg = useRef();

  // Load backend data
  useEffect(() => {
    if (!user) return;
    Promise.all([getGraph(), getCases(), getPipeline()])
      .then(([g, c, p]) => {
        setGraph(g);
        setCases(c);
        setPipeline(p);
        if (c && c.length > 0) {
          openCase(c[0].id);
        }
      })
      .catch((e) => setError(`${e.message}. Is the backend running at http://localhost:8000?`));
  }, [user]);

  const inCase = useMemo(() => {
    if (!active || !graph) return null;
    return new Set(graph.nodes.filter((n) => n.case === active).map((n) => n.id));
  }, [active, graph]);

  async function openCase(id) {
    setActive(id);
    setReport(null);
    setPicked(null);
    setEvidence(null);
    try {
      const ev = await getCase(id);
      setEvidence(ev);
    } catch (e) {
      setError(e.message);
    }
  }

  async function investigate(refresh = false) {
    if (!active) return;
    setLoading(true);
    setError("");
    try {
      const rep = await getReport(active, refresh);
      setReport(rep);
      setActiveTab("dossier");
    } catch (e) {
      setError(e.message);
    }
    setLoading(false);
  }

  // Filtered graph dataset
  const data = useMemo(() => {
    if (!graph) return null;
    let nodes = graph.nodes.map((n) => ({ ...n }));
    let links = graph.links.map((l) => ({ ...l }));

    if (filterType !== "all") {
      const validIds = new Set(nodes.filter((n) => n.type === filterType).map((n) => n.id));
      nodes = nodes.filter((n) => validIds.has(n.id));
      links = links.filter((l) => validIds.has(l.source.id ?? l.source) && validIds.has(l.target.id ?? l.target));
    }
    return { nodes, links };
  }, [graph, filterType]);

  // Jump camera to node
  function focusNode(nodeId) {
    setPicked(nodeId);
    if (!data || !fg.current) return;
    const n = data.nodes.find((x) => x.id === nodeId);
    if (n && typeof n.x === "number") {
      fg.current.centerAt(n.x, n.y, 800);
      fg.current.zoom(3.5, 800);
    }
  }

  // Handle Search Input
  function handleSearch(e) {
    e.preventDefault();
    if (!searchQuery.trim() || !data) return;
    const q = searchQuery.trim().toLowerCase();
    const found = data.nodes.find(
      (n) => n.id.toLowerCase() === q || (n.label && n.label.toLowerCase().includes(q))
    );
    if (found) {
      focusNode(found.id);
      if (found.case && found.case !== active) {
        openCase(found.case);
      }
    } else {
      setError(`Entity "${searchQuery}" not found in current network.`);
      setTimeout(() => setError(""), 3500);
    }
  }

  if (!user) {
    return <LoginPage onLogin={(loggedUser) => setUser(loggedUser)} />;
  }

  return (
    <div className="h-screen flex flex-col bg-slate-100 font-sans text-slate-900 select-none overflow-hidden">
      {/* ------------------------------------------------------------- */}
      {/* 1. TOP COMMAND BAR (FINANCIAL INTELLIGENCE HEADER) */}
      {/* ------------------------------------------------------------- */}
      <header className="h-16 px-5 bg-slate-900 text-white flex items-center justify-between gap-4 border-b border-slate-800 shadow-md z-30 shrink-0">
        {/* Brand & Live Status */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-white font-bold shadow-lg shadow-cyan-500/20">
            🛡️
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold tracking-tight text-white leading-tight">
                AI Financial Crime Network Investigator
              </h1>
              <span className="hidden xl:inline-flex items-center gap-1 text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                Live FIU Engine
              </span>
            </div>
            <p className="text-xs text-slate-400 hidden sm:block">
              Multi-Entity Deterministic Graph Analytics · Topologic Loop Search · Gemini Case Dossiers
            </p>
          </div>
        </div>

        {/* Center: Search & Quick Find */}
        <div className="hidden lg:flex items-center gap-2 flex-1 max-w-md mx-4">
          <form onSubmit={handleSearch} className="relative w-full">
            <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400 text-xs">
              🔍
            </span>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search entity ID (e.g. ACC-101, DEV-7, CUS-2)..."
              className="w-full pl-8 pr-16 py-1.5 text-xs rounded-lg bg-slate-800/90 border border-slate-700 text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition"
            />
            <button
              type="submit"
              className="absolute inset-y-1 right-1 px-2.5 bg-slate-700 hover:bg-slate-600 text-slate-200 text-[11px] font-medium rounded transition"
            >
              Locate
            </button>
          </form>
        </div>

        {/* Right Tools & Analyst Profile */}
        <div className="flex items-center gap-3">
          {/* Direct Link to Streamlit 7-CSV App */}
          <a
            href="http://localhost:8501"
            target="_blank"
            rel="noreferrer"
            title="Open the Streamlit 7-CSV Ingestion & Anomaly Detection Dashboard"
            className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-500 hover:to-cyan-500 text-white text-xs font-semibold shadow-md shadow-teal-500/10 transition active:scale-95"
          >
            <span>📂 7-CSV Upload Portal</span>
            <span className="text-[10px] bg-white/20 px-1 rounded font-mono">:8501 ↗</span>
          </a>

          {/* Upload Modal Trigger */}
          <button
            onClick={() => setShowUploadModal(true)}
            title="Inspect 7-CSV File Specifications & Ingestion Status"
            className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition flex items-center gap-1.5"
          >
            <span>📤 Ingest Specs</span>
          </button>

          {/* User Profile Pill */}
          <div className="hidden md:flex items-center gap-2 pl-3 border-l border-slate-800">
            <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-bold text-cyan-400">
              {user.name ? user.name[0] : "A"}
            </div>
            <div className="text-right">
              <div className="flex items-center gap-1.5 justify-end">
                <span className="text-xs font-semibold text-slate-200">{user.name}</span>
                <span className="text-[10px] px-1 py-0.2 rounded bg-slate-800 text-slate-300 font-mono border border-slate-700">
                  {user.badge}
                </span>
              </div>
              <p className="text-[10px] text-cyan-400 font-medium tracking-tight">
                {user.role} · <span className="text-emerald-400">{user.clearance}</span>
              </p>
            </div>
          </div>

          {/* Sign Out Button */}
          <button
            onClick={() => {
              localStorage.removeItem("fincrime_user");
              setUser(null);
            }}
            title="Sign out of analyst workstation"
            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition text-sm"
          >
            🚪
          </button>
        </div>
      </header>

      {/* Alert Banner if any error */}
      {error && (
        <div className="bg-rose-50 border-b border-rose-200 text-rose-800 px-5 py-2 text-xs flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-2">
            <span className="font-bold text-rose-600">⚠️ Notice:</span>
            <span>{error}</span>
          </div>
          <button onClick={() => setError("")} className="text-rose-600 hover:text-rose-900 font-bold text-sm">
            ✕
          </button>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 3. MAIN WORKSPACE (SPLIT SCREEN GRAPH & INVESTIGATION DOSSIER) */}
      {/* ------------------------------------------------------------- */}
      <div className="flex-1 flex flex-col md:flex-row min-h-0 overflow-hidden relative">
        {/* LEFT / CENTER: INTERACTIVE FORCE GRAPH CANVAS */}
        <main className="relative flex-1 min-h-[380px] bg-white overflow-hidden flex flex-col">
          {/* FLOATING TOP-LEFT: CASE SELECTOR HUD */}
          <div className="absolute top-3 left-3 z-10 flex flex-wrap items-center gap-1.5 glass-panel p-2 rounded-xl shadow-lg border border-slate-200/80">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider px-1.5 flex items-center gap-1">
              <span>🎯 Focus Ring:</span>
            </span>

            <button
              onClick={() => {
                setActive(null);
                setEvidence(null);
                setReport(null);
                setPicked(null);
              }}
              className={`text-xs px-2.5 py-1 rounded-lg font-semibold transition shadow-xs ${
                !active
                  ? "bg-slate-900 text-white shadow-md shadow-slate-900/20"
                  : "bg-white hover:bg-slate-100 text-slate-700 border border-slate-200"
              }`}
            >
              All Entities ({graph?.nodes?.length || 0})
            </button>

            {cases.map((c) => {
              const isSelected = active === c.id;
              const isCrit = c.score >= 90;
              return (
                <button
                  key={c.id}
                  onClick={() => openCase(c.id)}
                  className={`text-xs px-2.5 py-1 rounded-lg font-semibold transition flex items-center gap-1.5 shadow-xs ${
                    isSelected
                      ? "bg-rose-600 text-white shadow-md shadow-rose-600/30 scale-102 ring-2 ring-rose-400/50"
                      : "bg-white hover:bg-slate-50 text-slate-700 border border-slate-200"
                  }`}
                >
                  {isCrit && <span className="w-1.5 h-1.5 rounded-full bg-rose-400 animate-pulse" />}
                  <span>{c.id}</span>
                  <span
                    className={`text-[10px] px-1 py-0.2 rounded font-mono ${
                      isSelected ? "bg-rose-700 text-white" : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {c.score}
                  </span>
                </button>
              );
            })}
          </div>

          {/* FLOATING TOP-RIGHT: GRAPH CONTROLS HUD */}
          <div className="absolute top-3 right-3 z-10 flex items-center gap-1.5 glass-panel p-1.5 rounded-xl shadow-md border border-slate-200/80 text-xs">
            {/* Filter by Entity Type */}
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="text-xs bg-white border border-slate-200 text-slate-700 rounded-lg px-2 py-1 font-medium focus:outline-none focus:ring-1 focus:ring-cyan-500"
            >
              <option value="all">Filter: All Types</option>
              <option value="account">Accounts Only</option>
              <option value="customer">Customers Only</option>
              <option value="device">Devices Only</option>
              <option value="ip">IPs Only</option>
              <option value="merchant">Merchants Only</option>
            </select>

            {/* Toggle Labels */}
            <button
              onClick={() => setShowLabels(!showLabels)}
              title="Toggle node label visibility"
              className={`px-2.5 py-1 rounded-lg border font-medium transition ${
                showLabels
                  ? "bg-cyan-50 border-cyan-300 text-cyan-800"
                  : "bg-white border-slate-200 text-slate-600 hover:bg-slate-50"
              }`}
            >
              🏷️ Labels {showLabels ? "ON" : "OFF"}
            </button>

            {/* Fit View */}
            <button
              onClick={() => {
                if (fg.current) {
                  fg.current.zoomToFit(600, 30);
                }
              }}
              title="Reset Zoom & Fit Full Network"
              className="px-2.5 py-1 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 font-medium transition shadow-xs"
            >
              ⛶ Fit View
            </button>
          </div>

          {/* GRAPH CANVAS CONTAINER */}
          <div className="flex-1 w-full h-full relative bg-slate-50/40">
            {!data ? (
              <div className="h-full flex flex-col items-center justify-center gap-3 text-slate-500">
                <div className="w-8 h-8 border-3 border-cyan-500 border-t-transparent rounded-full animate-spin" />
                <p className="text-sm font-medium">Constructing multi-entity graph simulation…</p>
              </div>
            ) : (
              <ForceGraph2D
                ref={fg}
                graphData={data}
                nodeId="id"
                backgroundColor="#f8fafc"
                linkDirectionalArrowLength={(l) => (l.txn ? 4.5 : 0)}
                linkLineDash={(l) => (l.type === "SAME_AS" ? [3, 2] : null)}
                linkDirectionalArrowRelPos={1}
                linkColor={(l) => {
                  const s = l.source.id ?? l.source;
                  const t = l.target.id ?? l.target;
                  if (inCase) {
                    return inCase.has(s) && inCase.has(t) ? "#e11d48" : "#e2e8f0";
                  }
                  return l.type === "SAME_AS" ? "#9333ea" : "#cbd5e1";
                }}
                linkWidth={(l) => {
                  const s = l.source.id ?? l.source;
                  const t = l.target.id ?? l.target;
                  if (inCase && inCase.has(s) && inCase.has(t)) return 2.2;
                  return 0.7;
                }}
                nodeCanvasObject={(n, ctx, scale) => {
                  const isDimmed = inCase && !inCase.has(n.id);
                  const isHighlighted = n.id === picked || (inCase && inCase.has(n.id) && n.flagged);
                  const cfg = TYPE_CONFIG[n.type] || { color: "#64748b" };
                  const r = n.type === "account" ? 5.5 : 4.5;

                  ctx.globalAlpha = isDimmed ? 0.12 : 1;

                  // Node Circle Body
                  ctx.beginPath();
                  ctx.arc(n.x, n.y, r, 0, 2 * Math.PI);
                  ctx.fillStyle = cfg.color;
                  ctx.fill();

                  // Highlight Ring / Flagged Border
                  if (isHighlighted) {
                    ctx.lineWidth = 2.2 / Math.max(scale, 1);
                    ctx.strokeStyle = n.id === picked ? "#0f172a" : "#e11d48";
                    ctx.stroke();

                    // Outer pulse ring
                    ctx.beginPath();
                    ctx.arc(n.x, n.y, r + 3, 0, 2 * Math.PI);
                    ctx.lineWidth = 1 / Math.max(scale, 1);
                    ctx.strokeStyle = n.id === picked ? "rgba(15, 23, 42, 0.4)" : "rgba(225, 29, 72, 0.4)";
                    ctx.stroke();
                  } else {
                    ctx.lineWidth = 1 / Math.max(scale, 1);
                    ctx.strokeStyle = "#ffffff";
                    ctx.stroke();
                  }

                  // Node Label
                  if (showLabels && (scale > 1.8 || (inCase && inCase.has(n.id)) || n.id === picked)) {
                    ctx.font = `600 ${11 / Math.max(scale, 1.3)}px Inter, system-ui, sans-serif`;
                    ctx.fillStyle = isDimmed ? "#94a3b8" : "#0f172a";
                    ctx.fillText(n.label || n.id, n.x + r + 3, n.y + 3);
                  }

                  ctx.globalAlpha = 1;
                }}
                onNodeClick={(n) => {
                  setPicked(n.id);
                  if (n.case && n.case !== active) {
                    openCase(n.case);
                  }
                }}
                cooldownTicks={100}
              />
            )}
          </div>

          {/* FLOATING BOTTOM-LEFT: INTERACTIVE LEGEND */}
          <div className="absolute left-3 bottom-3 z-10 glass-panel p-2.5 rounded-xl shadow-md border border-slate-200/80 flex flex-wrap items-center gap-3 text-xs">
            <span className="font-bold text-slate-700 text-[11px] uppercase tracking-wider">Legend:</span>
            {Object.entries(TYPE_CONFIG).map(([k, cfg]) => (
              <span key={k} className="flex items-center gap-1 text-slate-700 font-medium">
                <span className="w-2.5 h-2.5 rounded-full shadow-xs" style={{ background: cfg.color }} />
                <span>{cfg.label}</span>
              </span>
            ))}
            <span className="flex items-center gap-1 text-rose-700 font-medium">
              <span className="w-2.5 h-2.5 rounded-full border-2 border-rose-600 shadow-xs" />
              <span>Flagged</span>
            </span>
          </div>

          {/* FLOATING BOTTOM-RIGHT: GRAPH METRIC PILL */}
          <div className="absolute right-3 bottom-3 z-10 glass-panel px-3 py-1.5 rounded-lg shadow-sm border border-slate-200/80 text-[11px] text-slate-600 hidden sm:flex items-center gap-2">
            <span>
              Entities: <b className="text-slate-900">{data?.nodes?.length || 0}</b>
            </span>
            <span>·</span>
            <span>
              Transactions: <b className="text-slate-900">{data?.links?.length || 0}</b>
            </span>
            <span>·</span>
            <span className="text-teal-700 font-semibold">Deterministic Subgraphs</span>
          </div>
        </main>

        {/* ------------------------------------------------------------- */}
        {/* RIGHT SIDEBAR: INTELLIGENCE CASE DOSSIER & AI REPORTING */}
        {/* ------------------------------------------------------------- */}
        <aside className="w-full md:w-[410px] lg:w-[460px] shrink-0 bg-slate-50 border-t md:border-t-0 md:border-l border-slate-200 flex flex-col h-auto md:h-full max-h-[50vh] md:max-h-full overflow-hidden shadow-xl z-20">
          {/* Aside Header & Tab Navigation */}
          <div className="p-3 bg-white border-b border-slate-200 shadow-xs shrink-0">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-base font-bold text-slate-900">Case Investigation</span>
                {active && (
                  <span className="text-xs px-2 py-0.5 rounded-md font-bold bg-rose-100 text-rose-700 border border-rose-200">
                    {active}
                  </span>
                )}
              </div>
              <span className="text-xs text-slate-500 font-medium">
                {cases.length} syndicate clusters identified
              </span>
            </div>

            {/* Sub-Tabs: Overview vs Dossier vs Transactions */}
            <div className="grid grid-cols-3 gap-1 bg-slate-100 p-1 rounded-lg text-xs font-semibold">
              <button
                onClick={() => setActiveTab("overview")}
                className={`py-1.5 rounded-md transition ${
                  activeTab === "overview" ? "bg-white text-slate-900 shadow-xs" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                🚩 Cases ({cases.length})
              </button>
              <button
                onClick={() => setActiveTab("dossier")}
                className={`py-1.5 rounded-md transition ${
                  activeTab === "dossier" ? "bg-white text-slate-900 shadow-xs" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                📑 AI Dossier
              </button>
              <button
                onClick={() => setActiveTab("ledger")}
                className={`py-1.5 rounded-md transition ${
                  activeTab === "ledger" ? "bg-white text-slate-900 shadow-xs" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                💸 Ledger ({evidence?.transactions?.length || 0})
              </button>
            </div>
          </div>

          {/* Aside Scrollable Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* TAB 1: CASES OVERVIEW & ACTIVE EVIDENCE */}
            {activeTab === "overview" && (
              <div className="space-y-4">
                {/* Flagged Cases Selector Carousel */}
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                    Prioritized Threat Rings
                  </h3>
                  <div className="space-y-2">
                    {cases.map((c) => {
                      const isSel = active === c.id;
                      const sev = c.score >= 90 ? "critical" : c.score >= 70 ? "high" : "medium";
                      const sevStyle = SEV_CONFIG[sev] || SEV_CONFIG.medium;
                      return (
                        <div
                          key={c.id}
                          onClick={() => openCase(c.id)}
                          className={`p-3 rounded-xl border transition cursor-pointer ${
                            isSel
                              ? "bg-white border-rose-500 shadow-md ring-1 ring-rose-400/40"
                              : "bg-white/80 hover:bg-white border-slate-200 hover:border-slate-300"
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1.5">
                            <div className="flex items-center gap-2">
                              <span className={`w-2 h-2 rounded-full ${sevStyle.dot}`} />
                              <span className="font-bold text-sm text-slate-900">{c.id}</span>
                              <span className="text-xs text-slate-500">· {c.entities} entities</span>
                            </div>
                            <span className={`text-xs px-2 py-0.5 rounded-md font-bold font-mono ${sevStyle.badge}`}>
                              {c.score}/100
                            </span>
                          </div>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {Object.keys(c.signals || {}).map((s) => (
                              <span
                                key={s}
                                className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-medium"
                              >
                                {s.replace(/_/g, " ")}
                              </span>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Active Case Scoreboard & Evidence Package */}
                {active && evidence && (
                  <div className="space-y-3 pt-2 border-t border-slate-200">
                    <AssessmentCard
                      a={evidence.assessment}
                      signals={evidence.signal_points}
                      picked={picked}
                      onPick={focusNode}
                    />

                    {/* AI Generation Callout */}
                    <div className="p-3 bg-gradient-to-br from-slate-900 to-cyan-950 text-white rounded-xl shadow-lg border border-slate-800 space-y-2.5">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5 text-cyan-400 text-xs font-bold uppercase tracking-wider">
                          <span>✨</span>
                          <span>Gemini AI FIU Dossier</span>
                        </div>
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-900/60 text-cyan-300 border border-cyan-700">
                          Hypothesis Testing
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed">
                        Synthesizes multi-hop money laundering signals, checks benign corporate alternatives, and drafts
                        admissible compliance SAR recommendations.
                      </p>
                      <button
                        onClick={() => investigate(false)}
                        disabled={loading}
                        className="w-full py-2 px-3 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs shadow-md shadow-cyan-500/20 transition flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer active:scale-98"
                      >
                        {loading ? (
                          <>
                            <span className="w-3.5 h-3.5 border-2 border-slate-900 border-t-transparent rounded-full animate-spin" />
                            <span>Synthesizing Forensic Intelligence…</span>
                          </>
                        ) : report ? (
                          <span>📑 View Complete Case Report</span>
                        ) : (
                          <span>⚡ Generate Official AI Case Report</span>
                        )}
                      </button>
                    </div>

                    {/* Identity Resolution Summary */}
                    <IdentityCard r={pipeline?.resolution} />
                  </div>
                )}
              </div>
            )}

            {/* TAB 2: AI CASE DOSSIER & COMPLIANCE REPORT */}
            {activeTab === "dossier" && (
              <div>
                {!report ? (
                  <div className="p-8 text-center space-y-3 bg-white rounded-xl border border-slate-200">
                    <div className="text-3xl">📑</div>
                    <h4 className="text-sm font-bold text-slate-800">No Report Generated Yet</h4>
                    <p className="text-xs text-slate-500 leading-relaxed">
                      Click below to let the AI intelligence agent evaluate the evidence package for{" "}
                      <b>{active || "the active case"}</b>.
                    </p>
                    <button
                      onClick={() => investigate(false)}
                      disabled={loading}
                      className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold transition shadow-md"
                    >
                      {loading ? "Generating…" : "Generate AI Case Report"}
                    </button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                      <div>
                        <span className="text-xs font-bold text-slate-900">FIU Case Dossier</span>
                        <p className="text-[11px] text-slate-500">Case ID: {active}</p>
                      </div>
                      <button
                        onClick={() => investigate(true)}
                        disabled={loading}
                        className="text-xs px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold border border-slate-300 transition"
                      >
                        🔄 Regenerate
                      </button>
                    </div>

                    <ReportViewer r={report} picked={picked} onPick={focusNode} />
                  </div>
                )}
              </div>
            )}

            {/* TAB 3: MONEY MOVEMENT LEDGER (TRANSACTIONS) */}
            {activeTab === "ledger" && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Audit Trail & Transactions ({evidence?.transactions?.length || 0})
                  </h3>
                  <span className="text-[11px] text-slate-500">Click row to focus node</span>
                </div>

                {!evidence?.transactions || evidence.transactions.length === 0 ? (
                  <p className="p-4 text-xs text-slate-500 bg-white rounded-lg border text-center">
                    No financial transactions recorded for this specific cluster.
                  </p>
                ) : (
                  <div className="space-y-1.5">
                    {evidence.transactions.map((t, idx) => (
                      <div
                        key={t.txn || idx}
                        onClick={() => focusNode(t.source)}
                        className={`p-2.5 rounded-lg border text-xs transition cursor-pointer ${
                          picked === t.txn || picked === t.source
                            ? "bg-cyan-50 border-cyan-400 shadow-xs"
                            : "bg-white hover:bg-slate-50 border-slate-200"
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-mono font-bold text-slate-800">{t.txn}</span>
                          <span className="font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                            ${t.amount ? t.amount.toLocaleString() : "0"}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5 text-slate-600 text-[11px]">
                          <span className="font-mono bg-slate-100 px-1 rounded">{t.source}</span>
                          <span>→</span>
                          <span className="font-mono bg-slate-100 px-1 rounded">{t.target}</span>
                        </div>
                        <div className="text-[10px] text-slate-400 mt-1">
                          {t.ts ? t.ts.replace("T", " ") : "Timestamped"}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </aside>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* 4. MODAL: 7-CSV UPLOAD SPECIFICATIONS & INGESTION STATUS */}
      {/* ------------------------------------------------------------- */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
            <div className="p-5 bg-slate-900 text-white flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <span>📂</span>
                  <span>7-CSV Ingestion Architecture & Data Center</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Expected schema format, mandatory columns, and partial dataset tolerance
                </p>
              </div>
              <button
                onClick={() => setShowUploadModal(false)}
                className="w-7 h-7 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 flex items-center justify-center font-bold"
              >
                ✕
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4 text-xs text-slate-700">
              <div className="p-3 bg-teal-50 border border-teal-200 rounded-xl flex items-center justify-between">
                <div>
                  <b className="text-teal-900 text-sm">Need to upload or replace CSV files?</b>
                  <p className="text-teal-700 mt-0.5">
                    The Streamlit app is the designated 7-file drag-and-drop upload center.
                  </p>
                </div>
                <a
                  href="http://localhost:8501"
                  target="_blank"
                  rel="noreferrer"
                  className="px-3 py-1.5 bg-teal-700 hover:bg-teal-800 text-white font-bold rounded-lg transition shrink-0"
                >
                  Open Upload Page ↗
                </a>
              </div>

              <h4 className="font-bold text-slate-900 text-sm">Expected 7 Entity Schemas:</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <SchemaCard
                  name="Transactions"
                  file="transactions.csv"
                  req="transaction_id, source_account_id, target_account_id, amount, timestamp"
                />
                <SchemaCard
                  name="Customers"
                  file="customers.csv"
                  req="customer_id, full_name, risk_rating, phone_number, email"
                />
                <SchemaCard
                  name="Accounts"
                  file="accounts.csv"
                  req="account_id, customer_id, account_type, balance, status"
                />
                <SchemaCard
                  name="Beneficiaries"
                  file="beneficiaries.csv"
                  req="account_id, beneficiary_account, name, relationship"
                />
                <SchemaCard
                  name="Merchants"
                  file="merchants.csv"
                  req="merchant_id, merchant_name, risk_level, category"
                />
                <SchemaCard
                  name="Device Activity"
                  file="device_activity.csv"
                  req="device_id, customer_id, ip_address, location, timestamp"
                />
                <SchemaCard
                  name="Fraud Alerts"
                  file="fraud_alerts.csv"
                  req="alert_id, entity_id, alert_type, severity, timestamp"
                />
              </div>
            </div>

            <div className="p-4 bg-slate-50 border-t border-slate-200 flex justify-end">
              <button
                onClick={() => setShowUploadModal(false)}
                className="px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-bold hover:bg-slate-800"
              >
                Close Window
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// -------------------------------------------------------------
// SUB-COMPONENTS & CARDS
// -------------------------------------------------------------

function AssessmentCard({ a, signals, picked, onPick }) {
  if (!a) return <p className="text-xs text-slate-500">Loading evidence...</p>;

  return (
    <div className="space-y-3">
      {/* 3 Metrics Scoreboard */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="bg-white p-2.5 rounded-xl border border-rose-200 shadow-xs">
          <p className="text-[10px] font-bold uppercase tracking-wider text-rose-700">Risk Score</p>
          <p className="text-xl font-extrabold text-rose-600 leading-tight">{a.risk_score}</p>
          <p className="text-[10px] font-semibold text-rose-500 uppercase">{a.risk_level}</p>
        </div>

        <div className="bg-white p-2.5 rounded-xl border border-slate-200 shadow-xs">
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Evidence</p>
          <p className="text-base font-extrabold text-slate-800 leading-tight mt-1">{a.evidence_strength}</p>
          <p className="text-[10px] text-slate-400">Multi-point</p>
        </div>

        <div className="bg-white p-2.5 rounded-xl border border-cyan-200 shadow-xs">
          <p className="text-[10px] font-bold uppercase tracking-wider text-cyan-700">Confidence</p>
          <p className="text-xl font-extrabold text-cyan-700 leading-tight">{a.confidence}%</p>
          <p className="text-[10px] text-cyan-500">Verified</p>
        </div>
      </div>

      {/* Signal breakdown */}
      {signals && Object.keys(signals).length > 0 && (
        <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
          <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2">
            Forensic Risk Points
          </h4>
          <div className="space-y-1.5">
            {Object.entries(signals).map(([sig, val]) => (
              <div key={sig} className="flex items-center justify-between text-xs">
                <span className="text-slate-600 capitalize">{sig.replace(/_/g, " ")}</span>
                <span className="font-mono font-bold text-rose-600 bg-rose-50 px-1.5 rounded border border-rose-200">
                  +{val}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Evidence items */}
      {a.evidence_items && (
        <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
          <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2">
            Gathered Graph Evidence
          </h4>
          <ul className="space-y-2 text-xs">
            {a.evidence_items.map((it, idx) => (
              <li key={idx} className="space-y-1">
                <div className="flex items-start gap-1.5">
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-900 text-white shrink-0">
                    {it.strength}
                  </span>
                  <span className="text-slate-700">{it.observation}</span>
                </div>
                <div className="flex flex-wrap gap-1 ml-4">
                  {[...new Set(it.records || [])].map((rec) => (
                    <button
                      key={rec}
                      onClick={() => onPick(rec)}
                      className={`text-[10px] font-mono px-1.5 py-0.5 rounded border transition ${
                        picked === rec ? "bg-slate-900 text-white" : "bg-slate-100 hover:bg-slate-200 text-slate-800"
                      }`}
                    >
                      {rec}
                    </button>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function ReportViewer({ r, picked, onPick }) {
  return (
    <article className="space-y-3 text-xs text-slate-800 bg-white p-4 rounded-xl border border-slate-200 shadow-sm leading-relaxed">
      {/* Verdict header */}
      <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 flex items-center justify-between">
        <div>
          <span className="text-[10px] font-bold uppercase tracking-wider text-rose-600">Investigative Verdict</span>
          <p className="text-sm font-black text-rose-950 uppercase">{r.verdict?.replace(/_/g, " ") || "SUSPICIOUS"}</p>
        </div>
        <span className="text-[10px] font-semibold text-slate-500 bg-white px-2 py-1 rounded border">
          Source: {r.source || "Gemini AI"}
        </span>
      </div>

      {/* Summary */}
      <div>
        <h4 className="font-bold text-slate-900 mb-1">Executive Summary:</h4>
        <p className="text-slate-700 bg-slate-50 p-2.5 rounded-lg border border-slate-200/80">{r.summary}</p>
      </div>

      {/* Pattern Analysis */}
      {r.pattern_analysis && (
        <div>
          <h4 className="font-bold text-slate-900 mb-1">Money Flow & Topological Pattern:</h4>
          <p className="text-slate-700">{r.pattern_analysis}</p>
        </div>
      )}

      {/* Narrative */}
      {r.narrative && (
        <div>
          <h4 className="font-bold text-slate-900 mb-1">Investigative Narrative:</h4>
          <div className="space-y-1.5 text-slate-700">
            {r.narrative
              .split("\n")
              .filter(Boolean)
              .map((p, i) => (
                <p key={i}>{p}</p>
              ))}
          </div>
        </div>
      )}

      {/* Hypotheses */}
      {r.hypotheses?.length > 0 && (
        <div>
          <h4 className="font-bold text-slate-900 mb-1.5">Hypotheses Evaluation:</h4>
          <div className="space-y-2">
            {r.hypotheses.map((h, i) => (
              <div key={i} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900">{h.title}</span>
                  <span className="font-bold text-slate-700">{Math.round((h.confidence || 0) * 100)}% Conf.</span>
                </div>
                <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-slate-900 h-full rounded-full" style={{ width: `${(h.confidence || 0) * 100}%` }} />
                </div>
                {h.note && <p className="text-[11px] text-slate-600">{h.note}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {r.recommended_actions?.length > 0 && (
        <div>
          <h4 className="font-bold text-slate-900 mb-1">Actionable Compliance Next Steps:</h4>
          <ul className="list-disc ml-5 space-y-1 text-slate-700">
            {r.recommended_actions.map((act, i) => (
              <li key={i}>{act}</li>
            ))}
          </ul>
        </div>
      )}
    </article>
  );
}

function IdentityCard({ r }) {
  if (!r) return null;
  return (
    <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-xs space-y-2 text-xs">
      <h4 className="font-bold text-slate-800 uppercase tracking-wider text-[11px]">
        Identity Resolution Links
      </h4>
      {r.matches?.map((m) => (
        <div key={m.a + m.b} className="p-2 rounded-lg bg-teal-50 border border-teal-200 text-teal-900">
          <p className="font-bold">
            {m.a} ⟷ {m.b} ({Math.round(m.confidence * 100)}% Match)
          </p>
          <p className="text-[10px] text-teal-700 mt-0.5">{m.reasons?.join(", ")}</p>
        </div>
      ))}
    </div>
  );
}

function SchemaCard({ name, file, req }) {
  return (
    <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
      <b className="text-slate-900 text-xs font-bold">{name}</b>
      <p className="font-mono text-[10px] text-cyan-700">{file}</p>
      <p className="text-[10px] text-slate-600 mt-1">
        <span className="font-semibold">Cols:</span> {req}
      </p>
    </div>
  );
}
