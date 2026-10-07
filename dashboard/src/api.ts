import type { AppConfig, Appeal, Metrics, Summary } from "./types";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      message = (await response.json()).error ?? message;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

export const api = {
  config: () => request<AppConfig>("/api/config"),
  summary: () => request<Summary>("/api/summary"),
  appeals: () => request<Appeal[]>("/api/appeals"),
  /** Metrics are optional: the server returns 404 when the model was not evaluated. */
  metrics: () => request<Metrics>("/api/metrics").catch(() => null),
  /** The same metrics on the appeals being served; 404 when they carry no known category. */
  liveMetrics: () => request<Metrics>("/api/metrics/live").catch(() => null),
  review: (id: string, category: string) =>
    request<Appeal>(`/api/appeals/${encodeURIComponent(id)}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category }),
    }),
  close: (id: string) =>
    request<Appeal>(`/api/appeals/${encodeURIComponent(id)}/close`, { method: "POST" }),
};
