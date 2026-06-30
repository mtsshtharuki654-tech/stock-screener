import { useState } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import type { ScreenHit } from "../types";
import clsx from "clsx";
import DualChartLayout from "../components/chart/DualChartLayout";
import { useChartData } from "../hooks/useChartData";
import { getCachedHit } from "../hooks/useScreener";
import type { IndexCorrelation, CorporateEvents } from "../types";
import { CONDITION_LABELS, LONG_CONDITIONS } from "../types";
import { fetchEvents } from "../api/client";

function CorrInfo({ corr }: { corr: IndexCorrelation | null }) {
  if (!corr) return null;
  const color =
    corr.label === "指数連動型"
      ? "text-blue-400"
      : corr.label === "逆相関型"
      ? "text-orange-400"
      : "text-emerald-400";
  return (
    <span className={clsx("text-xs", color)}>
      [{corr.label}] β={corr.beta} R={corr.correlation} vs {corr.index_name}（直近60日）
      {corr.beta_label && <span className="ml-1 text-gray-500">({corr.beta_label})</span>}
    </span>
  );
}

function AlertBadges({ events }: { events?: CorporateEvents }) {
  if (!events) return null;
  const items: { label: string; color: string }[] = [];
  if (events.warrant) items.push({ label: "ワラント", color: "bg-red-700 text-red-100" });
  if (events.secondary_offer) items.push({ label: "公募増資", color: "bg-red-700 text-red-100" });
  if (events.earnings_revision_down) items.push({ label: "業績下方", color: "bg-red-600 text-red-100" });
  if (events.earnings_near) items.push({ label: `決算${events.earnings_days_until}日後`, color: "bg-yellow-600 text-yellow-100" });
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

export default function StockDetailPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const hit =
    (location.state as { hit?: ScreenHit } | null)?.hit ??
    (code ? getCachedHit(code) : null);
  const { data: weeklyData } = useChartData(code ?? null, "weekly", 52);

  const [events, setEvents] = useState<CorporateEvents | null>(null);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [eventsError, setEventsError] = useState(false);
  const [eventsFetched, setEventsFetched] = useState(false);

  const handleFetchEvents = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!code) return;
    setEventsLoading(true);
    setEventsError(false);
    try {
      const data = await fetchEvents(code);
      setEvents(data);
      setEventsFetched(true);
    } catch {
      setEventsError(true);
    } finally {
      setEventsLoading(false);
    }
  };

  if (!code) return null;

  const hasAnyAlert = events
    ? events.warrant || events.secondary_offer || events.earnings_near ||
      events.earnings_revision_up || events.earnings_revision_down || events.buyback
    : false;

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-gray-950">
      {/* ヘッダー */}
      <header className="flex items-start gap-3 px-4 py-2 bg-gray-900 border-b border-gray-800 flex-shrink-0">
        <button
          onClick={() => navigate(-1)}
          className="text-gray-400 hover:text-white text-sm mt-0.5 flex-shrink-0"
        >
          ← 戻る
        </button>
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
          </div>
          <div className="flex flex-wrap items-center gap-2 mt-0.5">
            {/* ヒット条件 */}
            {hit?.conditions_matched.map((key) => {
              const isLong = LONG_CONDITIONS.includes(key as any);
              return (
                <span
                  key={key}
                  className={clsx(
                    "text-xs px-1.5 py-0.5 rounded font-semibold",
                    isLong ? "bg-emerald-800 text-emerald-200" : "bg-rose-800 text-rose-200"
                  )}
                >
                  {CONDITION_LABELS[key as keyof typeof CONDITION_LABELS] ?? key}
                </span>
              );
            })}

            {/* 注意情報 */}
            {eventsFetched ? (
              hasAnyAlert ? (
                <>
                  {hit?.conditions_matched.length ? <span className="text-gray-700 text-xs">|</span> : null}
                  <AlertBadges events={events!} />
                </>
              ) : (
                <span className="text-xs text-gray-500">注意情報なし</span>
              )
            ) : (
              <button
                onClick={handleFetchEvents}
                disabled={eventsLoading}
                className={clsx(
                  "text-xs px-2 py-0.5 rounded border transition-colors",
                  eventsLoading
                    ? "border-gray-600 text-gray-500 cursor-not-allowed"
                    : eventsError
                    ? "border-red-700 text-red-400 hover:bg-red-900"
                    : "border-gray-600 text-gray-400 hover:border-gray-400 hover:text-gray-200"
                )}
              >
                {eventsLoading ? "調査中…" : eventsError ? "再試行" : "注意情報を調べる"}
              </button>
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
      </header>

      {/* デュアルチャート */}
      <div className="flex-1 overflow-hidden">
        <DualChartLayout code={code} />
      </div>
    </div>
  );
}
