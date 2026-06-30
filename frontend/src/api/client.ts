import axios from "axios";
import type { ScreenRequest, ScreenResponse, ChartData, CorporateEvents } from "../types";

const api = axios.create({ baseURL: "/api", timeout: 30_000 });

// Viteプロキシ経由だとSSEが1イベント後にブロックされるため、
// 開発環境ではバックエンドに直接接続する。
const SSE_BASE = import.meta.env.VITE_API_URL ?? "";

export function streamScreen(
  req: ScreenRequest,
  onProgress: (msg: string, pct: number, elapsed: number, eta: number | null) => void,
  onResult: (res: ScreenResponse) => void,
  onError: (msg: string) => void,
): () => void {
  const ctrl = new AbortController();

  fetch(`${SSE_BASE}/api/screen`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(req),
    signal: ctrl.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const text = await res.text();
        onError(`サーバーエラー (${res.status}): ${text}`);
        return;
      }
      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data:")) continue;
          try {
            const payload = JSON.parse(line.slice(5).trim());
            if (payload.type === "progress")
              onProgress(payload.message, payload.pct ?? 0, payload.elapsed ?? 0, payload.eta ?? null);
            else if (payload.type === "result") onResult(payload.data as ScreenResponse);
            else if (payload.type === "error") onError(payload.message);
          } catch {}
        }
      }
    })
    .catch((e) => {
      if (e?.name !== "AbortError") onError(e?.message ?? "通信エラー");
    });

  return () => ctrl.abort();
}

export async function fetchChart(
  code: string,
  timeframe: "weekly" | "daily",
  periods = 200
): Promise<ChartData> {
  const { data } = await api.get<ChartData>(`/stocks/${code}/chart`, {
    params: { timeframe, periods },
  });
  return data;
}

export async function fetchEvents(code: string): Promise<CorporateEvents> {
  const { data } = await api.get<CorporateEvents>(`/events/${code}`);
  return data;
}

export async function checkHealth(): Promise<boolean> {
  try {
    await api.get("/health");
    return true;
  } catch {
    return false;
  }
}
