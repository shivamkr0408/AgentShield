// REST helpers and a reconnecting WebSocket client.
// - Same-origin by default (FastAPI serves the dashboard; nginx proxies it).
// - When the dashboard is hosted apart from the API (e.g. Vercel + Render), set VITE_API_URL
//   to the API's base URL; requests and the WebSocket (wss://) are routed there.
const BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

async function request(path, options) {
  const response = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) throw new Error(`${options?.method || "GET"} ${path} -> ${response.status}`);
  return response.json();
}

export const api = {
  config: () => request("/config"),
  stats: () => request("/stats"),
  events: (limit = 60) => request(`/events?limit=${limit}`),
  incidents: () => request("/incidents"),
  incident: (id) => request(`/incidents/${id}`),
  approvals: (status = "pending") => request(`/approvals?status=${status}`),
  approve: (id) => request(`/approvals/${id}/approve`, { method: "POST" }),
  deny: (id) => request(`/approvals/${id}/deny`, { method: "POST" }),
  policy: () => request("/policy"),
  updatePolicy: (body) => request("/policy", { method: "PUT", body: JSON.stringify(body) }),
  scan: (content, source = "playground") =>
    request("/scan", { method: "POST", body: JSON.stringify({ content, source }) }),
};

// Connects to /ws/events, calls onEvent for each message and onStatus with the connection
// state, and reconnects automatically with a capped backoff if the socket drops.
export function connectEvents(onEvent, onStatus) {
  let socket;
  let closed = false;
  let delay = 1000;

  const open = () => {
    let url;
    if (BASE) {
      url = `${BASE.replace(/^http/, "ws")}/ws/events`; // https -> wss, http -> ws
    } else {
      const scheme = location.protocol === "https:" ? "wss" : "ws";
      url = `${scheme}://${location.host}/ws/events`;
    }
    socket = new WebSocket(url);
    onStatus?.("connecting");
    socket.onopen = () => {
      delay = 1000;
      onStatus?.("connected");
    };
    socket.onmessage = (message) => {
      const data = JSON.parse(message.data);
      if (data.type !== "hello") onEvent(data);
    };
    socket.onclose = () => {
      onStatus?.("disconnected");
      if (!closed) {
        setTimeout(open, delay);
        delay = Math.min(delay * 2, 15000);
      }
    };
    socket.onerror = () => socket.close();
  };

  open();
  return () => {
    closed = true;
    socket?.close();
  };
}
