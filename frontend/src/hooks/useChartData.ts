import { useQuery } from "@tanstack/react-query";
import { fetchChart } from "../api/client";

export function useChartData(
  code: string | null,
  timeframe: "weekly" | "daily",
  periods = 200
) {
  return useQuery({
    queryKey: ["chart", code, timeframe, periods],
    queryFn: () => fetchChart(code!, timeframe, periods),
    enabled: !!code,
    staleTime: 1000 * 60 * 5,
  });
}
