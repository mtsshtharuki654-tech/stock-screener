import { useState } from "react";
import clsx from "clsx";
import ChartContainer from "./ChartContainer";
import ChartToolbar from "./ChartToolbar";
import { useChartData } from "../../hooks/useChartData";

interface Props {
  code: string;
}

const LEFT_PERIODS = { monthly: 60, weekly: 104 } as const;
const LEFT_LABELS  = { monthly: "月足", weekly: "週足" } as const;

export default function DualChartLayout({ code }: Props) {
  const [showCandles, setShowCandles] = useState(true);
  const [leftTf, setLeftTf] = useState<"weekly" | "monthly">("weekly");

  const left  = useChartData(code, leftTf, LEFT_PERIODS[leftTf]);
  const daily = useChartData(code, "daily", 120);

  const isLoading = left.isLoading || daily.isLoading;
  const error = left.error || daily.error;

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-500">
        チャートデータを取得中...
      </div>
    );
  }

  if (error || !left.data || !daily.data) {
    return (
      <div className="flex-1 flex items-center justify-center text-red-400">
        チャートデータの取得に失敗しました
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* 共通ツールバー */}
      <ChartToolbar
        timeframe="weekly"
        onTimeframeChange={() => {}}
        showCandles={showCandles}
        onToggleCandles={() => setShowCandles((v) => !v)}
      />

      {/* 2ペインレイアウト */}
      <div className="flex-1 grid grid-cols-2 gap-px bg-gray-800 overflow-hidden min-h-0">
        {/* 左ペイン（月足 / 週足 切替） */}
        <div className="bg-gray-950 flex flex-col min-h-0">
          <div className="px-3 py-1 text-xs text-gray-500 border-b border-gray-800 flex items-center gap-2">
            <span className="font-semibold text-gray-300">{LEFT_LABELS[leftTf]}</span>
            <span className="text-gray-600">環境認識・銘柄絞込</span>
            <div className="ml-auto flex gap-1">
              {(["monthly", "weekly"] as const).map((tf) => (
                <button
                  key={tf}
                  onClick={() => setLeftTf(tf)}
                  className={clsx(
                    "text-[10px] px-1.5 py-0.5 rounded border transition-colors",
                    leftTf === tf
                      ? "bg-blue-700 border-blue-500 text-white"
                      : "border-gray-700 text-gray-500 hover:text-gray-300"
                  )}
                >
                  {LEFT_LABELS[tf]}
                </button>
              ))}
            </div>
          </div>
          <div className="flex-1 min-h-0">
            <ChartContainer data={left.data} showCandles={showCandles} height={460} />
          </div>
        </div>

        {/* 右ペイン（日足・120本固定） */}
        <div className="bg-gray-950 flex flex-col min-h-0">
          <div className="px-3 py-1 text-xs text-gray-500 border-b border-gray-800 flex items-center gap-2">
            <span className="font-semibold text-gray-300">日足</span>
            <span className="text-gray-600">エントリータイミング</span>
          </div>
          <div className="flex-1 min-h-0">
            <ChartContainer data={daily.data} showCandles={showCandles} height={460} />
          </div>
        </div>
      </div>
    </div>
  );
}
