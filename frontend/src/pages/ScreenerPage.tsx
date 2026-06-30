import { useCallback, useRef, useState } from "react";
import { useScreener } from "../hooks/useScreener";
import ScreenerPanel from "../components/screener/ScreenerPanel";
import ResultsTable from "../components/screener/ResultsTable";
import type { ConditionStat, WinrateMode } from "../types";
import { streamWinrateCompute } from "../api/client";

export default function ScreenerPage() {
  const { mutate, clearResult, data, isFromCache, isPending, progress, pct, elapsed, eta, error } = useScreener();

  const [winrateMode, setWinrateMode] = useState<WinrateMode>("lookup");
  const [backtestStats, setBacktestStats] = useState<Record<string, ConditionStat> | null>(null);
  const [backtestCompute, setBacktestCompute] = useState({
    isComputing: false,
    progress: "",
    pct: 0,
    error: null as string | null,
  });
  const cancelComputeRef = useRef<(() => void) | null>(null);

  const handleComputeBacktest = useCallback(() => {
    if (backtestCompute.isComputing) return;
    setBacktestCompute({ isComputing: true, progress: "", pct: 0, error: null });

    const cancel = streamWinrateCompute(
      (msg, pctVal) => {
        setBacktestCompute((s) => ({ ...s, progress: msg, pct: pctVal }));
      },
      (stats) => {
        setBacktestStats(stats);
        setBacktestCompute({ isComputing: false, progress: "", pct: 100, error: null });
      },
      (errMsg) => {
        setBacktestCompute((s) => ({ ...s, isComputing: false, error: errMsg }));
      },
    );
    cancelComputeRef.current = cancel;
  }, [backtestCompute.isComputing]);

  // スクリーナー結果にバックテスト統計が含まれていれば取り込む
  const effectiveBacktestStats = backtestStats ?? data?.backtest_stats ?? null;

  // 現在のモードに応じた統計を ScreenResponse に上書きして渡す
  const enrichedResult = data
    ? { ...data, backtest_stats: effectiveBacktestStats }
    : null;

  return (
    <div className="flex h-screen overflow-hidden">
      <ScreenerPanel onRun={mutate} isLoading={isPending} />
      <main className="flex-1 flex flex-col overflow-hidden">
        <ResultsTable
          result={enrichedResult ?? null}
          isFromCache={isFromCache}
          onClear={clearResult}
          isLoading={isPending}
          progress={progress}
          pct={pct}
          elapsed={elapsed}
          eta={eta}
          error={error}
          winrateMode={winrateMode}
          onWinrateModeChange={setWinrateMode}
          backtestCompute={backtestCompute}
          onComputeBacktest={handleComputeBacktest}
        />
      </main>
    </div>
  );
}
