import axios from "axios";
import type { ScreenRequest, ScreenResponse, ChartData } from "../types";

const api = axios.create({ baseURL: "/api", timeout: 30_000 });

export async function runScreen(req: ScreenRequest): Promise<ScreenResponse> {
  const { data } = await api.post<ScreenResponse>("/screen", req, {
    timeout: 600_000, // 初回データ取得は最大10分
  });
  return data;
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

export async function checkHealth(): Promise<boolean> {
  try {
    await api.get("/health");
    return true;
  } catch {
    return false;
  }
}
