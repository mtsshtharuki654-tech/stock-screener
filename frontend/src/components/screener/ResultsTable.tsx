import { useNavigate } from "react-router-dom";
import clsx from "clsx";
import type { ConditionStat, ScreenResponse, WinrateMode } from "../../types";
import ResultRow from "./ResultRow";

interface BacktestComputeState {
  isComputing: boolean;
  progress: string;
  pct: number;
  error: string | null;
}

interface Props {
  result: ScreenResponse | null;
  isFromCache?: boolean;
  onClear?: () => void;
  isLoading: boolean;
  progress: string;
  pct: number;
  elapsed: number;
  eta: number | null;
  error: Error | null;
  // 勝率モード
  winrateMode: WinrateMode;
  onWinrateModeChange: (mode: WinrateMode) => void;
  backtestCompute: BacktestComputeState;
  onComputeBacktest: () => void;
}

const HEADERS = [
  "コード", "銘柄名", "株価", "直近出来高", "週平均出来高",
  "シグナル", "翌週確率", "ヒット条件", "注意情報", "指数連動性",
];

function formatTime(secs: number): string {
  if (secs < 60) return `${secs}秒`;
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return s > 0 ? `${m}分${s}秒` : `${m}分`;
}

export default function ResultsTable({
  result,
  isFromCache,
  onClear,
  isLoading,
  progress,
  pct,
  elapsed,
  eta,
  error,
  winrateMode,
  onWinrateModeChange,
  backtestCompute,
  onComputeBacktest,
}: Props) {
  const navigate = useNavigate();

  if (isLoading) {
    const displayPct = Math.max(0, Math.min(100, pct));
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="w-full max-w-md px-8">
          <div className="text-center mb-6">
            <div className="text-4xl mb-4 animate-spin">⟳</div>
            <p className="text-gray-300 font-medium">{progress || "処理中..."}</p>
            <p className="text-gray-500 text-sm mt-2">初回はJ-Quantsからデータを取得するため<br />数分かかります。そのままお待ちください。</p>
          </div>

          <div className="w-full bg-gray-800 rounded-full h-3 mb-3 overflow-hidden">
            <div
              className="h-3 rounded-full bg-blue-500 transition-all duration-500"
              style={{ width: `${displayPct}%` }}
            />
          </div>

          <div className="flex justify-between text-sm text-gray-400">
            <span>{displayPct.toFixed(1)}%</span>
            <span className="flex gap-3">
              {elapsed > 0 && <span>経過 {formatTime(elapsed)}</span>}
              {eta != null && eta > 0 && <span>残り約 {formatTime(eta)}</span>}
            </span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center text-red-400">
          <p className="text-xl mb-2">エラーが発生しました</p>
          <p className="text-sm text-gray-500">{error.message}</p>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-600">
        <div className="text-center">
          <p className="text-2xl mb-2">条件を設定してスクリーニングを実行してください</p>
          <p className="text-sm">左パネルで条件を選択し、「スクリーニング実行」ボタンを押してください</p>
        </div>
      </div>
    );
  }

  const conditionStats: Record<string, ConditionStat> | null =
    winrateMode === "backtest"
      ? (result.backtest_stats ?? null)
      : (result.lookup_stats ?? null);

  const hasBacktest = result.backtest_stats != null;

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* 前回の結果バナー */}
      {isFromCache && (
        <div className="px-4 py-1.5 bg-yellow-900/40 border-b border-yellow-700/50 flex items-center gap-3 text-xs text-yellow-300">
          <span>前回のスクリーニング結果を表示中（{new Date(result.screened_at).toLocaleString("ja-JP")}）</span>
          <button
            onClick={onClear}
            className="ml-auto px-2 py-0.5 rounded bg-yellow-700/50 hover:bg-yellow-600/60 text-yellow-200 text-xs"
          >
            クリア
          </button>
        </div>
      )}

      {/* サマリー + 勝率モード切替 */}
      <div className="px-4 py-2 bg-gray-900 border-b border-gray-800 flex flex-wrap items-center gap-3 text-sm text-gray-400">
        <span>ユニバース: <strong className="text-white">{result.total_universe.toLocaleString()}</strong> 銘柄</span>
        <span>ヒット: <strong className="text-blue-400">{result.hits.length}</strong> 銘柄</span>
        <span>処理時間: {(result.duration_ms / 1000).toFixed(1)}秒</span>

        {/* 勝率モードセレクター */}
        <div className="ml-auto flex items-center gap-2">
          <span className="text-xs text-gray-500">勝率表示:</span>
          <div className="flex rounded overflow-hidden border border-gray-700 text-xs">
            <button
              onClick={() => onWinrateModeChange("lookup")}
              className={clsx(
                "px-2.5 py-1 transition-colors",
                winrateMode === "lookup"
                  ? "bg-blue-700 text-white"
                  : "bg-gray-800 text-gray-400 hover:bg-gray-700"
              )}
            >
              理論値
            </button>
            <button
              onClick={() => onWinrateModeChange("backtest")}
              className={clsx(
                "px-2.5 py-1 transition-colors border-l border-gray-700",
                winrateMode === "backtest"
                  ? "bg-blue-700 text-white"
                  : "bg-gray-800 text-gray-400 hover:bg-gray-700"
              )}
            >
              バックテスト
            </button>
          </div>

          {/* バックテストモード選択時のアクション */}
          {winrateMode === "backtest" && (
            backtestCompute.isComputing ? (
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <span className="animate-spin text-blue-400">⟳</span>
                <span>{backtestCompute.progress || "計算中..."}</span>
                <span className="text-gray-600">
                  {backtestCompute.pct > 0 ? `${backtestCompute.pct.toFixed(0)}%` : ""}
                </span>
              </div>
            ) : backtestCompute.error ? (
              <button
                onClick={onComputeBacktest}
                className="text-xs px-2 py-1 rounded border border-red-700 text-red-400 hover:bg-red-900 transition-colors"
              >
                再試行
              </button>
            ) : !hasBacktest ? (
              <button
                onClick={onComputeBacktest}
                className="text-xs px-2 py-1 rounded border border-indigo-600 text-indigo-300 hover:bg-indigo-900 transition-colors"
              >
                バックテスト計算する
              </button>
            ) : (
              <button
                onClick={onComputeBacktest}
                className="text-xs px-2 py-1 rounded border border-gray-600 text-gray-400 hover:border-gray-400 hover:text-gray-200 transition-colors"
              >
                再計算
              </button>
            )
          )}
        </div>

        <span className="text-xs text-gray-600">{new Date(result.screened_at).toLocaleString("ja-JP")}</span>
      </div>

      {/* バックテスト計算中の進捗バー */}
      {backtestCompute.isComputing && backtestCompute.pct > 0 && (
        <div className="h-1 bg-gray-800">
          <div
            className="h-1 bg-indigo-500 transition-all duration-300"
            style={{ width: `${Math.min(100, backtestCompute.pct)}%` }}
          />
        </div>
      )}

      {result.hits.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-gray-600">
          <p>条件にヒットする銘柄が見つかりませんでした</p>
        </div>
      ) : (
        <div className="flex-1 overflow-auto">
          <table className="w-full text-left text-gray-100 min-w-max">
            <thead className="bg-gray-900 sticky top-0">
              <tr>
                {HEADERS.map((h) => (
                  <th key={h} className="px-3 py-2 text-xs text-gray-400 font-semibold uppercase whitespace-nowrap border-b border-gray-800">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.hits.map((hit) => (
                <ResultRow
                  key={hit.code}
                  hit={hit}
                  onClick={() => navigate(`/stock/${hit.code}`, { state: { hit } })}
                  conditionStats={conditionStats ?? undefined}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
