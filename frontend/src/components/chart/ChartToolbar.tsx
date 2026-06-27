import clsx from "clsx";

interface Props {
  timeframe: "weekly" | "daily";
  onTimeframeChange: (tf: "weekly" | "daily") => void;
  showCandles: boolean;
  onToggleCandles: () => void;
}

export default function ChartToolbar({
  timeframe,
  onTimeframeChange,
  showCandles,
  onToggleCandles,
}: Props) {
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-900 border-b border-gray-800">
      {/* 週足/日足 */}
      {(["weekly", "daily"] as const).map((tf) => (
        <button
          key={tf}
          onClick={() => onTimeframeChange(tf)}
          className={clsx(
            "text-xs px-2.5 py-1 rounded font-medium transition-colors",
            timeframe === tf
              ? "bg-blue-600 text-white"
              : "bg-gray-800 text-gray-400 hover:text-white"
          )}
        >
          {tf === "weekly" ? "週足" : "日足"}
        </button>
      ))}

      {/* 裸チャートトグル */}
      <button
        onClick={onToggleCandles}
        className={clsx(
          "ml-2 text-xs px-2.5 py-1 rounded font-medium border transition-colors",
          showCandles
            ? "border-gray-700 text-gray-400 hover:text-white"
            : "border-blue-500 text-blue-400 bg-blue-950"
        )}
        title={showCandles ? "ローソク足を非表示（裸チャート）" : "ローソク足を表示"}
      >
        {showCandles ? "ローソク足 ON" : "裸チャート"}
      </button>

      {/* MA凡例 */}
      <div className="ml-auto flex items-center gap-3 text-xs text-gray-400">
        <span><span className="inline-block w-3 h-0.5 bg-blue-500 mr-1" />5MA</span>
        <span><span className="inline-block w-3 h-0.5 bg-orange-500 mr-1" />20MA</span>
        <span><span className="inline-block w-3 h-0.5 bg-red-500 mr-1" />60MA</span>
      </div>
    </div>
  );
}
