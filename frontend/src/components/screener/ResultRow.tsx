import clsx from "clsx";
import type { ScreenHit } from "../../types";
import { CONDITION_LABELS, LONG_CONDITIONS } from "../../types";

interface Props {
  hit: ScreenHit;
  onClick: () => void;
}

function EventBadges({ events }: { events: ScreenHit["corporate_events"] }) {
  const badges: { label: string; color: string; priority: number }[] = [];

  if (events.under_supervision)
    badges.push({ label: "監理銘柄", color: "bg-red-800 text-red-100", priority: 0 });
  if (events.warrant.detected)
    badges.push({ label: "ワラント", color: "bg-red-700 text-red-100", priority: 1 });
  if (events.secondary_offer.detected)
    badges.push({ label: "公募増資", color: "bg-red-700 text-red-100", priority: 1 });
  if (events.margin_restriction)
    badges.push({ label: "信用規制", color: "bg-red-700 text-red-100", priority: 1 });
  if (events.earnings_revision_down.detected)
    badges.push({ label: "業績下方", color: "bg-red-600 text-red-100", priority: 2 });
  if (events.tob.detected)
    badges.push({ label: "TOB", color: "bg-yellow-700 text-yellow-100", priority: 3 });
  if (events.earnings.is_near && events.earnings.days_until != null)
    badges.push({ label: `決算${events.earnings.days_until}日後`, color: "bg-yellow-600 text-yellow-100", priority: 3 });
  if (events.large_holder.detected)
    badges.push({ label: "大量保有", color: "bg-blue-700 text-blue-100", priority: 4 });
  if (events.split.recent)
    badges.push({ label: "株分割済", color: "bg-blue-600 text-blue-100", priority: 5 });
  if (events.buyback.detected)
    badges.push({ label: "自社株買", color: "bg-emerald-700 text-emerald-100", priority: 6 });
  if (events.earnings_revision_up.detected)
    badges.push({ label: "業績上方", color: "bg-emerald-600 text-emerald-100", priority: 6 });

  badges.sort((a, b) => a.priority - b.priority);

  return (
    <div className="flex flex-wrap gap-1">
      {badges.map((b) => (
        <span key={b.label} className={clsx("text-xs px-1.5 py-0.5 rounded font-medium", b.color)}>
          {b.label}
        </span>
      ))}
    </div>
  );
}

function CorrBadge({ corr }: { corr: ScreenHit["index_correlation"] }) {
  if (!corr) return null;
  const color =
    corr.label === "指数連動型"
      ? "text-blue-300"
      : corr.label === "逆相関型"
      ? "text-orange-300"
      : "text-emerald-300";
  return (
    <span className={clsx("text-xs", color)}>
      {corr.label} β{corr.beta}
    </span>
  );
}

// hit object is passed via router state so StockDetailPage can show corporate events
export default function ResultRow({ hit, onClick }: Props) {
  const isLong = hit.signal_type === "long" || hit.signal_type === "mixed";
  const isShort = hit.signal_type === "short" || hit.signal_type === "mixed";

  return (
    <tr
      onClick={onClick}
      className="border-b border-gray-800 hover:bg-gray-800 cursor-pointer transition-colors"
    >
      {/* コード・銘柄名 */}
      <td className="px-3 py-2 text-sm font-mono text-blue-400">{hit.code}</td>
      <td className="px-3 py-2 text-sm">
        <div className="font-medium">{hit.name}</div>
        <span className={clsx(
          "text-xs px-1 rounded",
          hit.segment === "Prime" ? "bg-violet-900 text-violet-200" : "bg-teal-900 text-teal-200"
        )}>
          {hit.segment}
        </span>
      </td>
      {/* 株価 */}
      <td className="px-3 py-2 text-sm text-right font-mono">
        {hit.last_price.toLocaleString()}円
      </td>
      {/* 直近出来高 */}
      <td className="px-3 py-2 text-sm text-right font-mono text-gray-300">
        {(hit.last_volume / 10000).toFixed(1)}万
      </td>
      {/* 週平均出来高 */}
      <td className="px-3 py-2 text-sm text-right font-mono text-gray-400">
        {(hit.avg_weekly_volume / 10000).toFixed(1)}万
      </td>
      {/* シグナル */}
      <td className="px-3 py-2">
        <div className="flex gap-1">
          {isLong && <span className="text-xs bg-emerald-800 text-emerald-200 px-1.5 py-0.5 rounded">Long</span>}
          {isShort && <span className="text-xs bg-rose-800 text-rose-200 px-1.5 py-0.5 rounded">Short</span>}
        </div>
      </td>
      {/* ヒット条件 */}
      <td className="px-3 py-2">
        <div className="flex flex-wrap gap-1">
          {hit.conditions_matched.map((key) => {
            const isL = LONG_CONDITIONS.includes(key as any);
            return (
              <span
                key={key}
                className={clsx(
                  "text-xs px-1.5 py-0.5 rounded",
                  isL ? "bg-emerald-900 text-emerald-300" : "bg-rose-900 text-rose-300"
                )}
              >
                {CONDITION_LABELS[key as keyof typeof CONDITION_LABELS] ?? key}
              </span>
            );
          })}
        </div>
      </td>
      {/* 注意情報 */}
      <td className="px-3 py-2">
        <EventBadges events={hit.corporate_events} />
      </td>
      {/* 指数連動性 */}
      <td className="px-3 py-2">
        <CorrBadge corr={hit.index_correlation} />
      </td>
    </tr>
  );
}
