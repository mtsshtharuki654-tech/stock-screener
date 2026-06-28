import { useState } from "react";
import ChartContainer from "./ChartContainer";
import ChartToolbar from "./ChartToolbar";
import { useChartData } from "../../hooks/useChartData";

interface Props {
  code: string;
}

export default function DualChartLayout({ code }: Props) {
  const [showCandles, setShowCandles] = useState(true);
  const [weeklyTf] = useState<"weekly">("weekly");
  const [dailyTf] = useState<"daily">("daily");

  const weekly = useChartData(code, weeklyTf, 26);  // 約6ヶ月（環境認識用）
  const daily = useChartData(code, dailyTf, 65);    // 約3ヶ月（エントリー用）

  const isLoading = weekly.isLoading || daily.isLoading;
  const error = weekly.error || daily.error;

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-500">
        チャートデータを取得中...
      </div>
    );
  }

  if (error || !weekly.data || !daily.data) {
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
        {/* 週足 */}
        <div className="bg-gray-950 flex flex-col min-h-0">
          <div className="px-3 py-1 text-xs text-gray-500 border-b border-gray-800 flex items-center gap-2">
            <span className="font-semibold text-gray-300">週足</span>
            <span className="text-gray-600">環境認識・銘柄絞込</span>
          </div>
          <div className="flex-1 min-h-0">
            <ChartContainer data={weekly.data} showCandles={showCandles} height={460} />
          </div>
        </div>

        {/* 日足 */}
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
