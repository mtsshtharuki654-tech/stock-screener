import { useState } from "react";
import clsx from "clsx";
import type { ConditionKey, ScreenRequest } from "../../types";
import {
  LONG_CONDITIONS,
  SHORT_CONDITIONS,
  CONDITION_LABELS,
} from "../../types";

interface Props {
  onRun: (req: ScreenRequest) => void;
  isLoading: boolean;
}

const ALL_CONDITIONS: ConditionKey[] = [...LONG_CONDITIONS, ...SHORT_CONDITIONS];

export default function ScreenerPanel({ onRun, isLoading }: Props) {
  const [segments, setSegments] = useState<("Prime" | "Growth")[]>(["Prime", "Growth"]);
  const [minVolume, setMinVolume] = useState(100000);
  const [maxPrice, setMaxPrice] = useState(5000);
  const [conditions, setConditions] = useState<ConditionKey[]>(ALL_CONDITIONS);

  function toggleSegment(seg: "Prime" | "Growth") {
    setSegments((prev) =>
      prev.includes(seg) ? prev.filter((s) => s !== seg) : [...prev, seg]
    );
  }

  function toggleCondition(key: ConditionKey) {
    setConditions((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  }

  function toggleGroup(keys: ConditionKey[], checked: boolean) {
    if (checked) {
      setConditions((prev) => Array.from(new Set([...prev, ...keys])));
    } else {
      setConditions((prev) => prev.filter((k) => !keys.includes(k)));
    }
  }

  function handleRun() {
    if (segments.length === 0 || conditions.length === 0) return;
    onRun({ conditions, min_volume: minVolume, max_price: maxPrice, segments });
  }

  return (
    <aside className="w-64 min-w-[256px] bg-gray-900 border-r border-gray-800 flex flex-col h-full overflow-y-auto p-4 gap-5">
      <h1 className="text-lg font-bold text-white">PPP株スクリーナー</h1>

      {/* 市場 */}
      <section>
        <p className="text-xs text-gray-400 font-semibold mb-2 uppercase tracking-widest">市場</p>
        {(["Prime", "Growth"] as const).map((seg) => (
          <label key={seg} className="flex items-center gap-2 text-sm cursor-pointer mb-1">
            <input
              type="checkbox"
              checked={segments.includes(seg)}
              onChange={() => toggleSegment(seg)}
              className="accent-blue-500"
            />
            <span>{seg}</span>
          </label>
        ))}
      </section>

      {/* フィルター */}
      <section>
        <p className="text-xs text-gray-400 font-semibold mb-2 uppercase tracking-widest">フィルター</p>
        <label className="block text-sm mb-1">
          出来高 ≥
          <input
            type="number"
            value={minVolume}
            onChange={(e) => setMinVolume(Number(e.target.value))}
            step={10000}
            className="mt-1 w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm"
          />
        </label>
        <label className="block text-sm mt-2">
          株価 ≤
          <input
            type="number"
            value={maxPrice}
            onChange={(e) => setMaxPrice(Number(e.target.value))}
            step={500}
            className="mt-1 w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm"
          />
        </label>
      </section>

      {/* ロング条件 */}
      <section>
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs text-emerald-400 font-semibold uppercase tracking-widest">ロング（買い）</p>
          <label className="flex items-center gap-1 text-xs text-gray-400 cursor-pointer">
            <input
              type="checkbox"
              checked={LONG_CONDITIONS.every((k) => conditions.includes(k))}
              onChange={(e) => toggleGroup(LONG_CONDITIONS, e.target.checked)}
              className="accent-emerald-500"
            />
            全選択
          </label>
        </div>
        {LONG_CONDITIONS.map((key) => (
          <label key={key} className="flex items-center gap-2 text-sm cursor-pointer mb-1">
            <input
              type="checkbox"
              checked={conditions.includes(key)}
              onChange={() => toggleCondition(key)}
              className="accent-emerald-500"
            />
            <span>{CONDITION_LABELS[key]}</span>
          </label>
        ))}
      </section>

      {/* ショート条件 */}
      <section>
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs text-rose-400 font-semibold uppercase tracking-widest">ショート（売り）</p>
          <label className="flex items-center gap-1 text-xs text-gray-400 cursor-pointer">
            <input
              type="checkbox"
              checked={SHORT_CONDITIONS.every((k) => conditions.includes(k))}
              onChange={(e) => toggleGroup(SHORT_CONDITIONS, e.target.checked)}
              className="accent-rose-500"
            />
            全選択
          </label>
        </div>
        {SHORT_CONDITIONS.map((key) => (
          <label key={key} className="flex items-center gap-2 text-sm cursor-pointer mb-1">
            <input
              type="checkbox"
              checked={conditions.includes(key)}
              onChange={() => toggleCondition(key)}
              className="accent-rose-500"
            />
            <span>{CONDITION_LABELS[key]}</span>
          </label>
        ))}
      </section>

      {/* 実行ボタン */}
      <button
        onClick={handleRun}
        disabled={isLoading || segments.length === 0 || conditions.length === 0}
        className={clsx(
          "mt-auto w-full py-2.5 rounded font-bold text-sm transition-colors",
          isLoading
            ? "bg-gray-700 text-gray-400 cursor-not-allowed"
            : "bg-blue-600 hover:bg-blue-500 text-white"
        )}
      >
        {isLoading ? "スクリーニング中..." : "スクリーニング実行"}
      </button>
    </aside>
  );
}
