import { useEffect, useState } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import type { ConditionStat, ScreenHit } from "../types";
import clsx from "clsx";
import DualChartLayout from "../components/chart/DualChartLayout";
import { useChartData } from "../hooks/useChartData";
import { getCachedHit, getCachedScreenResult } from "../hooks/useScreener";
import type { IndexCorrelation, CorporateEvents } from "../types";
import { CONDITION_LABELS, LONG_CONDITIONS } from "../types";
import { fetchEvents } from "../api/client";

function CorrInfo({ corr }: { corr: IndexCorrelation | null }) {
  if (!corr) return null;
  const color =
    corr.label === "指数連動型" ? "text-blue-400"
    : corr.label === "逆相関型"  ? "text-orange-400"
    : "text-emerald-400";
  return (
    <span className={clsx("text-xs", color)}>
      [{corr.label}] β={corr.beta} R={corr.correlation} vs {corr.index_name}（直近60日）
      {corr.beta_label && <span className="ml-1 text-gray-500">({corr.beta_label})</span>}
    </span>
  );
}

function earningsBadgeColor(days: number): string {
  if (days <= 7)  return "bg-red-700 text-red-100";
  if (days <= 30) return "bg-orange-700 text-orange-100";
  if (days <= 60) return "bg-yellow-700 text-yellow-100";
  return "bg-gray-700 text-gray-300";
}

function AlertBadges({ events }: { events?: CorporateEvents }) {
  if (!events) return null;
  const items: { label: string; color: string }[] = [];
  if (events.warrant) items.push({ label: "ワラント", color: "bg-red-700 text-red-100" });
  if (events.secondary_offer) items.push({ label: "公募増資", color: "bg-red-700 text-red-100" });
  if (events.earnings_revision_down) items.push({ label: "業績下方", color: "bg-red-600 text-red-100" });
  if (events.earnings_days_until != null)
    items.push({ label: `決算${events.earnings_days_until}日後`, color: earningsBadgeColor(events.earnings_days_until) });
  if (events.buyback) items.push({ label: "自社株買", color: "bg-emerald-700 text-emerald-100" });
  if (events.earnings_revision_up) items.push({ label: "業績上方", color: "bg-emerald-600 text-emerald-100" });
  if (items.length === 0) return null;
  return (
    <div className="flex gap-1 flex-wrap">
      {items.map((i) => (
        <span key={i.label} className={clsx("text-xs px-1.5 py-0.5 rounded font-medium", i.color)}>{i.label}</span>
      ))}
    </div>
  );
}

function pctColor(rate: number): string {
  if (rate >= 0.70) return "text-emerald-300";
  if (rate >= 0.65) return "text-green-400";
  if (rate >= 0.60) return "text-yellow-400";
  return "text-gray-400";
}

function RsBadge({ rs }: { rs: number }) {
  const color =
    rs >= 5  ? "text-emerald-400"
    : rs >= 0  ? "text-green-400"
    : rs >= -5 ? "text-yellow-400"
    : "text-red-400";
  return (
    <span className={clsx("text-xs font-semibold", color)}>
      RS {rs >= 0 ? "+" : ""}{rs.toFixed(1)}%
    </span>
  );
}

function VolRatioBadge({ ratio }: { ratio: number }) {
  const color =
    ratio >= 2.0 ? "text-emerald-400"
    : ratio >= 1.5 ? "text-green-400"
    : ratio >= 1.0 ? "text-yellow-400"
    : "text-gray-500";
  return (
    <span className={clsx("text-xs font-semibold", color)}>
      出来高{ratio >= 1 ? "↑" : "↓"}{ratio.toFixed(1)}x
    </span>
  );
}

export default function StockDetailPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const location = useLocation();

  const hit =
    (location.state as { hit?: ScreenHit } | null)?.hit ??
    (code ? getCachedHit(code) : null);

  const { data: weeklyData } = useChartData(code ?? null, "weekly", 52);
  const [events, setEvents] = useState<CorporateEvents | null>(null);

  // マウント時に自動取得（codeが変わるたびにリセット＆再取得）
  useEffect(() => {
    setEvents(null);
    if (!code) return;
    fetchEvents(code).then(setEvents).catch(() => {});
  }, [code]);

  if (!code) return null;

  // スクリーナー結果から前後ナビゲーション
  const allHits = getCachedScreenResult()?.hits ?? [];
  const currentIdx = allHits.findIndex((h) => h.code === code);
  const prevHit = currentIdx > 0 ? allHits[currentIdx - 1] : null;
  const nextHit = currentIdx >= 0 && currentIdx < allHits.length - 1 ? allHits[currentIdx + 1] : null;

  const goTo = (target: ScreenHit) => {
    navigate(`/stock/${target.code}`, { state: { hit: target } });
  };

  const conditionStats: Record<string, ConditionStat> | null =
    getCachedScreenResult()?.lookup_stats ?? null;

  const hasAnyAlert = events != null && (
    events.warrant || events.secondary_offer || events.earnings_near ||
    events.earnings_revision_up || events.earnings_revision_down || events.buyback ||
    events.earnings_days_until != null
  );

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-gray-950">
      <header className="flex items-start gap-2 px-3 py-2 bg-gray-900 border-b border-gray-800 flex-shrink-0">

        {/* 戻る */}
        <button
          onClick={() => navigate(-1)}
          className="text-gray-400 hover:text-white text-sm mt-0.5 flex-shrink-0 px-1"
        >
          ←
        </button>

        {/* 銘柄情報 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-3 flex-wrap">
            <span className="text-base font-bold font-mono text-blue-400">{code}</span>
            {weeklyData && (
              <>
                <span className="text-base font-semibold">{weeklyData.name}</span>
                <span className="text-sm text-gray-300 font-mono">
                  {weeklyData.candles.at(-1)?.close.toLocaleString()}円
                </span>
              </>
            )}
            {/* 位置表示 */}
            {allHits.length > 0 && currentIdx >= 0 && (
              <span className="text-xs text-gray-500">
                {currentIdx + 1} / {allHits.length}
              </span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2 mt-0.5">
            {/* ヒット条件 */}
            {hit?.conditions_matched.map((key) => {
              const isLong = LONG_CONDITIONS.includes(key as any);
              const stat = conditionStats?.[key];
              const pct = stat?.win_rate != null ? Math.round(stat.win_rate * 100) : null;
              return (
                <span
                  key={key}
                  className={clsx(
                    "text-xs px-1.5 py-0.5 rounded font-semibold inline-flex items-center gap-1",
                    isLong ? "bg-emerald-800 text-emerald-200" : "bg-rose-800 text-rose-200"
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

            {/* 注意情報 */}
            {events == null ? (
              <span className="text-xs text-gray-600">取得中…</span>
            ) : hasAnyAlert ? (
              <>
                {hit?.conditions_matched.length ? <span className="text-gray-700 text-xs">|</span> : null}
                <AlertBadges events={events} />
              </>
            ) : (
              <span className="text-xs text-gray-500">注意情報なし</span>
            )}

            {/* RS・出来高比率・鮮度 */}
            {(hit?.rs_score != null || hit?.volume_ratio != null || hit?.signal_freshness_weeks != null) && (
              <>
                <span className="text-gray-700 text-xs">|</span>
                {hit.rs_score != null && <RsBadge rs={hit.rs_score} />}
                {hit.volume_ratio != null && <VolRatioBadge ratio={hit.volume_ratio} />}
                {hit.signal_freshness_weeks != null && (
                  <span className={clsx(
                    "text-xs font-semibold",
                    hit.signal_freshness_weeks <= 1 ? "text-blue-400"
                    : hit.signal_freshness_weeks <= 2 ? "text-indigo-400"
                    : hit.signal_freshness_weeks <= 3 ? "text-gray-400"
                    : "text-gray-600"
                  )}>
                    {hit.signal_freshness_weeks <= 1 ? "新規" : `${hit.signal_freshness_weeks}週`}
                  </span>
                )}
              </>
            )}

            {/* 指数連動性 */}
            {hit?.index_correlation && (
              <>
                <span className="text-gray-700 text-xs">|</span>
                <CorrInfo corr={hit.index_correlation} />
              </>
            )}
          </div>
        </div>

        {/* 前後ナビゲーション */}
        {allHits.length > 1 && (
          <div className="flex items-center gap-1 flex-shrink-0 mt-0.5">
            <button
              onClick={() => prevHit && goTo(prevHit)}
              disabled={!prevHit}
              title={prevHit ? `← ${prevHit.code} ${prevHit.name}` : ""}
              className={clsx(
                "flex flex-col items-center px-2.5 py-1 rounded text-xs transition-colors border",
                prevHit
                  ? "border-gray-600 text-gray-300 hover:bg-gray-700 hover:border-gray-400"
                  : "border-gray-800 text-gray-700 cursor-not-allowed"
              )}
            >
              <span className="text-base leading-none">‹</span>
              {prevHit && <span className="text-gray-500 text-[10px] leading-tight">{prevHit.code}</span>}
            </button>
            <button
              onClick={() => nextHit && goTo(nextHit)}
              disabled={!nextHit}
              title={nextHit ? `${nextHit.code} ${nextHit.name} →` : ""}
              className={clsx(
                "flex flex-col items-center px-2.5 py-1 rounded text-xs transition-colors border",
                nextHit
                  ? "border-gray-600 text-gray-300 hover:bg-gray-700 hover:border-gray-400"
                  : "border-gray-800 text-gray-700 cursor-not-allowed"
              )}
            >
              <span className="text-base leading-none">›</span>
              {nextHit && <span className="text-gray-500 text-[10px] leading-tight">{nextHit.code}</span>}
            </button>
          </div>
        )}
      </header>

      <div className="flex-1 overflow-hidden">
        <DualChartLayout code={code} />
      </div>
    </div>
  );
}
