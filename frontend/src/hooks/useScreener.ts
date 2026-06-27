import { useMutation } from "@tanstack/react-query";
import { runScreen } from "../api/client";
import type { ScreenRequest, ScreenResponse, ScreenHit } from "../types";

const STORAGE_KEY = "screener_hits";

export function getCachedHit(code: string): ScreenHit | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const map = JSON.parse(raw) as Record<string, ScreenHit>;
    return map[code] ?? null;
  } catch {
    return null;
  }
}

export function useScreener() {
  return useMutation<ScreenResponse, Error, ScreenRequest>({
    mutationFn: runScreen,
    onSuccess: (data) => {
      const map: Record<string, ScreenHit> = {};
      for (const hit of data.hits) map[hit.code] = hit;
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(map));
    },
  });
}
