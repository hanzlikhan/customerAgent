// API client for the DukaanAI FastAPI backend.
export const API_URL = (
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");
export const BUSINESS_ID = Number(import.meta.env.VITE_BUSINESS_ID || 1);

async function get(path) {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

async function post(path, body) {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export const api = {
  health: () => get("/health"),
  business: (id = BUSINESS_ID) => get(`/business/${id}`),
  evalLatest: () => get("/eval/latest"),
  summary: (id = BUSINESS_ID) =>
    get(`/dashboard/summary?business_id=${id}`),
  escalations: (id = BUSINESS_ID, status = "open") =>
    get(`/escalations?business_id=${id}&status=${status}`),
  resolveEscalation: (id, resolution) =>
    post(`/escalations/${id}/resolve`, { resolution: resolution || null }),
  conversations: (id = BUSINESS_ID, limit = 10) =>
    get(`/conversations?business_id=${id}&limit=${limit}`),
  messages: (id) => get(`/conversations/${id}/messages`),
  uploadCatalog: async (file, id = BUSINESS_ID) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(
      `${API_URL}/catalog/upload?business_id=${id}`,
      { method: "POST", body: form },
    );
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(detail.detail || `Upload failed (${res.status})`);
    }
    return res.json();
  },
  importCatalog: (rows, sourceDoc, id = BUSINESS_ID) =>
    post("/catalog/import", {
      business_id: id,
      rows,
      source_doc: sourceDoc,
    }),
};

/**
 * Live chat over Server-Sent Events. Returns the EventSource; the caller
 * should close it on unmount. Step events arrive in real time as each
 * agent node completes; exactly one result (or error) event ends it.
 */
export function streamChat(text, { onStep, onResult, onError }) {
  const params = new URLSearchParams({
    business_id: String(BUSINESS_ID),
    user_text: text,
    customer_ref: "react-demo",
  });
  const es = new EventSource(`${API_URL}/chat/stream?${params}`);
  es.addEventListener("step", (e) => {
    if (onStep) onStep(JSON.parse(e.data));
  });
  es.addEventListener("result", (e) => {
    if (onResult) onResult(JSON.parse(e.data));
    es.close();
  });
  es.addEventListener("error", (e) => {
    // Server-sent error events carry data; a bare network failure does not.
    if (e.data) {
      if (onError) onError(JSON.parse(e.data));
    } else if (es.readyState === EventSource.CLOSED) {
      if (onError) onError({ detail: "Connection to the API was lost." });
    }
    es.close();
  });
  return es;
}
