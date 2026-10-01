// REST helpers and a reconnecting WebSocket client. Same-origin in production (FastAPI serves
// the built dashboard); the Vite dev proxy forwards these paths to the API on :8000.

async function request(path, options) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) throw new Error(`${options?.method || "GET"} ${path} -> ${response.status}`);
  return response.json();
}

export const api = {
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
    const scheme = location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${scheme}://${location.host}/ws/events`);
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
