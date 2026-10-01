import { StrictMode, useCallback, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import { api, connectEvents } from "./api.js";
import { Approvals, Incidents, Overview, Playground, Policies, Results } from "./pages.jsx";

const PAGES = [
  { id: "overview", label: "Overview", icon: "📊" },
  { id: "incidents", label: "Incidents", icon: "🗂️" },
  { id: "approvals", label: "Approvals", icon: "✋" },
  { id: "playground", label: "Playground", icon: "🧪" },
  { id: "policies", label: "Policies", icon: "⚙️" },
  { id: "results", label: "Results", icon: "📈" },
];

const THREAT = new Set(["block", "blocked", "approval", "denied"]);

function useTheme() {
  const [theme, setTheme] = useState(() => localStorage.getItem("ags-theme") || "auto");
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "auto") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme);
    try { localStorage.setItem("ags-theme", theme); } catch {}
  }, [theme]);
  return [theme, setTheme];
}

function App() {
  const [route, setRoute] = useState("overview");
  const [events, setEvents] = useState([]);
  const [stats, setStats] = useState({});
  const [approvals, setApprovals] = useState([]);
  const [policy, setPolicy] = useState({});
  const [status, setStatus] = useState("connecting");
  const [demo, setDemo] = useState(false);
  const [toasts, setToasts] = useState([]);
  const [theme, setTheme] = useTheme();
  const toastId = useRef(0);

  const pushToast = useCallback((message, tone) => {
    const id = ++toastId.current;
    setToasts((list) => [...list, { id, message, tone }]);
    setTimeout(() => setToasts((list) => list.filter((t) => t.id !== id)), 5000);
  }, []);

  const refreshStats = useCallback(() => api.stats().then(setStats).catch(() => {}), []);
  const refreshApprovals = useCallback(() => api.approvals("pending").then(setApprovals).catch(() => {}), []);

  useEffect(() => {
    api.events(60).then((list) => setEvents(list)).catch(() => {});
    refreshStats();
    refreshApprovals();
    api.policy().then(setPolicy).catch(() => {});
    api.config().then((c) => setDemo(!!c.demo)).catch(() => {});
  }, [refreshStats, refreshApprovals]);

  useEffect(() => {
    const disconnect = connectEvents((event) => {
      setEvents((list) => [event, ...list].slice(0, 200));
      refreshStats();
      if (event.type === "approval" || event.outcome === "approval") refreshApprovals();
      if (event.outcome === "approval") pushToast(`Approval needed: ${event.tool}`, "warn");
      else if (THREAT.has(event.outcome)) pushToast(`Blocked: ${event.reason || event.tool}`, "danger");
    }, setStatus);
    return disconnect;
  }, [pushToast, refreshStats, refreshApprovals]);

  useEffect(() => {
    const onKey = (e) => {
      if (e.target.tagName === "TEXTAREA" || e.target.tagName === "INPUT") return;
      const index = Number(e.key) - 1;
      if (index >= 0 && index < PAGES.length) setRoute(PAGES[index].id);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const page = PAGES.find((p) => p.id === route);
  const pending = approvals.length;

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand"><span className="dot" /> <span>AgentShield</span></div>
        <nav className="nav">
          {PAGES.map((p, i) => (
            <button key={p.id} className={route === p.id ? "active" : ""} onClick={() => setRoute(p.id)}>
              <span className="ico">{p.icon}</span>
              <span className="text">{p.label}</span>
              {p.id === "approvals" && pending ? <span className="badge warn">{pending}</span> : <span className="key">{i + 1}</span>}
            </button>
          ))}
        </nav>
      </aside>

      <div className="main">
        <header className="topbar">
          <h1>{page.label}</h1>
          {demo ? <span className="badge warn" title="Running a small model or recorded data; full results are from the local system">Demo mode</span> : null}
          <span className="spacer" />
          <span className={`badge ${status === "connected" ? "ok" : status === "connecting" ? "warn" : "danger"}`}>
            <span className="dotpulse" /> {status}
          </span>
          <button className="icon" title="Toggle theme" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
            {theme === "dark" ? "☀️" : "🌙"}
          </button>
        </header>

        <main className="content">
          {route === "overview" && <Overview events={events} stats={stats} />}
          {route === "incidents" && <Incidents />}
          {route === "approvals" && <Approvals approvals={approvals} timeout={policy.approval_timeout_seconds || 30} refresh={refreshApprovals} />}
          {route === "playground" && <Playground />}
          {route === "policies" && <Policies policy={policy} onSaved={setPolicy} />}
          {route === "results" && <Results />}
        </main>
      </div>

      <nav className="tabbar">
        {PAGES.map((p) => (
          <button key={p.id} className={route === p.id ? "active" : ""} onClick={() => setRoute(p.id)}>
            <span className="ico">{p.icon}</span>
            {p.label}
          </button>
        ))}
      </nav>

      <div className="toasts">
        {toasts.map((t) => <div key={t.id} className={`toast ${t.tone === "warn" ? "warn" : ""}`}>{t.message}</div>)}
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<StrictMode><App /></StrictMode>);
