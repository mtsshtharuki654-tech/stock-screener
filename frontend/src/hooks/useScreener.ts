import { useState, useRef, useCallback } from "react";
import { streamScreen } from "../api/client";
import type { ScreenRequest, ScreenResponse, ScreenHit } from "../types";

const STORAGE_KEY = "screener_hits";
const RESULT_STORAGE_KEY = "screener_result";

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

function cacheHits(hits: ScreenHit[]) {
  const map: Record<string, ScreenHit> = {};
  for (const hit of hits) map[hit.code] = hit;
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(map));
}

function saveResult(res: ScreenResponse) {
  try {
    sessionStorage.setItem(RESULT_STORAGE_KEY, JSON.stringify(res));
  } catch {}
}

function loadResult(): ScreenResponse | null {
  try {
    const raw = sessionStorage.getItem(RESULT_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as ScreenResponse) : null;
  } catch {
    return null;
  }
}

export function getCachedScreenResult(): ScreenResponse | null {
  return loadResult();
}

export interface ScreenerState {
  data: ScreenResponse | null;
  isFromCache: boolean;
  isPending: boolean;
  progress: string;
  pct: number;
  elapsed: number;
  eta: number | null;
  error: Error | null;
}

export function useScreener() {
  const [state, setState] = useState<ScreenerState>(() => {
    const cached = loadResult();
    return {
      data: cached,
      isFromCache: cached !== null,
      isPending: false,
      progress: "",
      pct: 0,
      elapsed: 0,
      eta: null,
      error: null,
    };
  });
  const cancelRef = useRef<(() => void) | null>(null);

  const clearResult = useCallback(() => {
    sessionStorage.removeItem(RESULT_STORAGE_KEY);
    sessionStorage.removeItem(STORAGE_KEY);
    setState((s) => ({ ...s, data: null, isFromCache: false, error: null }));
  }, []);

  const mutate = useCallback((req: ScreenRequest) => {
    cancelRef.current?.();
    setState({ data: null, isFromCache: false, isPending: true, progress: "接続中...", pct: 0, elapsed: 0, eta: null, error: null });

    const cancel = streamScreen(
      req,
      (msg, pct, elapsed, eta) => setState((s) => ({ ...s, progress: msg, pct, elapsed, eta })),
      (res) => {
        cacheHits(res.hits);
        saveResult(res);
        setState({ data: res, isFromCache: false, isPending: false, progress: "", pct: 100, elapsed: 0, eta: null, error: null });
      },
      (msg) => setState({ data: null, isFromCache: false, isPending: false, progress: "", pct: 0, elapsed: 0, eta: null, error: new Error(msg) }),
    );
    cancelRef.current = cancel;
  }, []);

  return { ...state, mutate, clearResult };
}
