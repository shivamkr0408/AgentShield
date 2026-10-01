// Shared presentational pieces used across the dashboard pages.
import { Area, AreaChart, Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis } from "recharts";

const OUTCOME = {
  block: { cls: "danger", label: "blocked" },
  blocked: { cls: "danger", label: "blocked" },
  sanitize: { cls: "warn", label: "sanitized" },
  sanitized: { cls: "warn", label: "sanitized" },
  approval: { cls: "warn", label: "approval" },
  denied: { cls: "danger", label: "denied" },
  approved: { cls: "ok", label: "approved" },
  allow: { cls: "ok", label: "allowed" },
  allowed: { cls: "ok", label: "allowed" },
};

export function OutcomeBadge({ outcome }) {
  const meta = OUTCOME[outcome] || { cls: "muted", label: outcome || "—" };
  return <span className={`badge ${meta.cls}`}>{meta.label}</span>;
}

export function StatCard({ label, value, tone }) {
  return (
    <div className="card stat">
      <div className={`value ${tone || ""}`}>{value}</div>
      <div className="label">{label}</div>
    </div>
  );
}

export function RiskBar({ risk }) {
  const pct = Math.round((risk || 0) * 100);
  const color = risk >= 0.85 ? "var(--danger)" : risk >= 0.5 ? "var(--warn)" : "var(--ok)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 90 }}>
      <div className="bar" style={{ flex: 1 }}>
        <span style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="mono" style={{ fontSize: 12 }}>{pct}</span>
    </div>
  );
}

const CHART_COLORS = ["#d6455a", "#d98324", "#2f6fed", "#1a9c6b", "#8a5cf6"];

export function TrafficChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={data} margin={{ top: 6, right: 6, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2f6fed" stopOpacity={0.5} />
            <stop offset="100%" stopColor="#2f6fed" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#d6455a" stopOpacity={0.6} />
            <stop offset="100%" stopColor="#d6455a" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis dataKey="t" hide />
        <Tooltip contentStyle={tooltipStyle} />
        <Area type="monotone" dataKey="traffic" stroke="#2f6fed" fill="url(#g1)" strokeWidth={2} name="events" />
        <Area type="monotone" dataKey="threats" stroke="#d6455a" fill="url(#g2)" strokeWidth={2} name="threats" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function LayerBars({ data }) {
  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data} margin={{ top: 6, right: 6, left: 0, bottom: 0 }}>
        <XAxis dataKey="layer" tick={{ fill: "var(--muted)", fontSize: 12 }} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--surface-2)" }} />
        <Bar dataKey="count" radius={[6, 6, 0, 0]}>
          {data.map((_, index) => <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function AttackMix({ data }) {
  if (!data.length) return <p className="muted">No threats recorded yet.</p>;
  return (
    <ResponsiveContainer width="100%" height={180}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" innerRadius={42} outerRadius={70} paddingAngle={2}>
          {data.map((_, index) => <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} />)}
        </Pie>
        <Tooltip contentStyle={tooltipStyle} />
      </PieChart>
    </ResponsiveContainer>
  );
}

const tooltipStyle = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  color: "var(--text)",
  fontSize: 12,
};
