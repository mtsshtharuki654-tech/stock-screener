import { useEffect, useState } from "react";
import clsx from "clsx";
import type { ConditionStat, CorporateEvents, ScreenHit } from "../../types";
import { CONDITION_LABELS, LONG_CONDITIONS, SHORT_CONDITIONS } from "../../types";
import { fetchEvents } from "../../api/client";

interface Props {
  hit: ScreenHit;
  onClick: () => void;
  conditionStats?: Record<string, ConditionStat>;
}

function earningsBadgeColor(days: number): string {
  if (days <= 7)  return "bg-red-700 text-red-100";
  if (days <= 30) return "bg-orange-700 text-orange-100";
  if (days <= 60) return "bg-yellow-700 text-yellow-100";
  return "bg-gray-700 text-gray-300";
}

function EventBadges({ events }: { events: CorporateEvents }) {
  const badges: { label: string; color: string }[] = [];
  if (events.warrant)
    badges.push({ label: "ワラント", color: "bg-red-700 text-red-100" });
  if (events.secondary_offer)
    badges.push({ label: "公募増資", color: "bg-red-700 text-red-100" });
  if (events.earnings_revision_down)
    badges.push({ label: "業績下方", color: "bg-red-600 text-red-100" });
  if (events.earnings_days_until != null)
    badges.push({ label: `決算${events.earnings_days_until}日後`, color: earningsBadgeColor(events.earnings_days_until) });
  if (events.buyback)
    badges.push({ label: "自社株買", color: "bg-emerald-700 text-emerald-100" });
  if (events.earnings_revision_up)
    badges.push({ label: "業績上方", color: "bg-emerald-600 text-emerald-100" });

  if (badges.length === 0)
    return <span className="text-xs text-gray-600">—</span>;

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
    corr.label === "指数連動型" ? "text-blue-300"
    : corr.label === "逆相関型"  ? "text-orange-300"
    : "text-emerald-300";
  return <span className={clsx("text-xs", color)}>{corr.label} β{corr.beta}</span>;
}

function pctColor(rate: number): string {
  if (rate >= 0.70) return "text-emerald-300";
  if (rate >= 0.65) return "text-green-400";
  if (rate >= 0.60) return "text-yellow-400";
  return "text-gray-400";
}

function FreshnessBadge({ weeks }: { weeks: number }) {
  const cfg =
    weeks <= 1 ? { label: "新規", cls: "bg-blue-800 text-blue-200" }
    : weeks <= 2 ? { label: "2週", cls: "bg-indigo-900 text-indigo-300" }
    : weeks <= 3 ? { label: "3週", cls: "bg-gray-700 text-gray-300" }
    : { label: "古い", cls: "bg-gray-800 text-gray-500" };
  return (
    <span className={clsx("text-[10px] px-1 py-0.5 rounded font-medium", cfg.cls)}>
      {cfg.label}
    </span>
  );
}

function avgRate(keys: string[], stats: Record<string, ConditionStat> | undefined): number | null {
  if (!stats || keys.length === 0) return null;
  const rates = keys.map((k) => stats[k]?.win_rate).filter((r): r is number => r != null);
  if (rates.length === 0) return null;
  return rates.reduce((a, b) => a + b, 0) / rates.length;
}

function WinrateCell({ hit, conditionStats }: { hit: ScreenHit; conditionStats?: Record<string, ConditionStat> }) {
  const longKeys  = hit.conditions_matched.filter((k) => LONG_CONDITIONS.includes(k as any));
  const shortKeys = hit.conditions_matched.filter((k) => SHORT_CONDITIONS.includes(k as any));
  const longRate  = avgRate(longKeys, conditionStats);
  const shortRate = avgRate(shortKeys, conditionStats);

  if (longRate == null && shortRate == null)
    return <span className="text-xs text-gray-600">—</span>;

  return (
    <div className="flex flex-col gap-0.5">
      {longRate != null && (
        <span className={clsx("text-sm font-bold tabular-nums", pctColor(longRate))}>
          {Math.round(longRate * 100)}%
          <span className="text-xs font-normal ml-0.5 text-gray-400">上昇</span>
        </span>
      )}
      {shortRate != null && (
        <span className={clsx("text-sm font-bold tabular-nums", pctColor(shortRate))}>
          {Math.round(shortRate * 100)}%
          <span className="text-xs font-normal ml-0.5 text-gray-400">下落</span>
        </span>
      )}
    </div>
  );
}

export default function ResultRow({ hit, onClick, conditionStats }: Props) {
  const [events, setEvents] = useState<CorporateEvents | null>(null);

  // マウント時に自動取得
  useEffect(() => {
    let cancelled = false;
    fetchEvents(hit.code)
      .then((data) => { if (!cancelled) setEvents(data); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [hit.code]);

  const isLong  = hit.signal_type === "long"  || hit.signal_type === "mixed";
  const isShort = hit.signal_type === "short" || hit.signal_type === "mixed";

  return (
    <tr
      onClick={onClick}
      className="border-b border-gray-800 hover:bg-gray-800 cursor-pointer transition-colors"
    >
      {/* コード */}
      <td className="px-3 py-2 text-sm font-mono text-blue-400">{hit.code}</td>

      {/* 銘柄名 */}
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

      {/* 出来高 / 比率 */}
      <td className="px-3 py-2 text-sm text-right font-mono">
        <div className="text-gray-300">{(hit.last_volume / 10000).toFixed(1)}万</div>
        <div className="text-xs text-gray-500">avg {(hit.avg_weekly_volume / 10000).toFixed(1)}万</div>
        {hit.volume_ratio != null && (
          <div className={clsx(
            "text-xs font-bold tabular-nums",
            hit.volume_ratio >= 2.0 ? "text-emerald-400"
            : hit.volume_ratio >= 1.5 ? "text-green-400"
            : hit.volume_ratio >= 1.0 ? "text-yellow-400"
            : "text-gray-500"
          )}>
            {hit.volume_ratio >= 1.0 ? "↑" : "↓"}{hit.volume_ratio.toFixed(1)}x
          </div>
        )}
      </td>

      {/* シグナル / RS */}
      <td className="px-3 py-2">
        <div className="flex gap-1 flex-wrap">
          {isLong  && <span className="text-xs bg-emerald-800 text-emerald-200 px-1.5 py-0.5 rounded">Long</span>}
          {isShort && <span className="text-xs bg-rose-800 text-rose-200 px-1.5 py-0.5 rounded">Short</span>}
        </div>
        {hit.rs_score != null && (
          <div className={clsx(
            "text-xs font-semibold mt-0.5",
            hit.rs_score >= 5  ? "text-emerald-400"
            : hit.rs_score >= 0  ? "text-green-400"
            : hit.rs_score >= -5 ? "text-yellow-400"
            : "text-red-400"
          )}>
            RS {hit.rs_score >= 0 ? "+" : ""}{hit.rs_score.toFixed(1)}%
          </div>
        )}
      </td>

      {/* 翌週確率 */}
      <td className="px-3 py-2">
        <WinrateCell hit={hit} conditionStats={conditionStats} />
      </td>

      {/* ヒット条件 */}
      <td className="px-3 py-2">
        <div className="flex flex-wrap gap-1 items-center">
          {hit.conditions_matched.map((key) => {
            const isL = LONG_CONDITIONS.includes(key as any);
            const stat = conditionStats?.[key];
            const pct = stat?.win_rate != null ? Math.round(stat.win_rate * 100) : null;
            return (
              <span
                key={key}
                className={clsx(
                  "text-xs px-1.5 py-0.5 rounded inline-flex items-center gap-1",
                  isL ? "bg-emerald-900 text-emerald-300" : "bg-rose-900 text-rose-300"
                )}
              >
                {CONDITION_LABELS[key as keyof typeof CONDITION_LABELS] ?? key}
                {pct != null && (
                  <span className={clsx("font-semibold", pctColor(stat!.win_rate!))}>
                    {pct}%
                  </span>
                )}
              </span>
            );
          })}
          {hit.signal_freshness_weeks != null && (
            <FreshnessBadge weeks={hit.signal_freshness_weeks} />
          )}
        </div>
      </td>

      {/* 注意情報（自動表示） */}
      <td className="px-3 py-2">
        {events
          ? <EventBadges events={events} />
          : <span className="text-xs text-gray-700">取得中…</span>
        }
      </td>

      {/* 指数連動性 */}
      <td className="px-3 py-2">
        <CorrBadge corr={hit.index_correlation} />
      </td>
    </tr>
  );
}
