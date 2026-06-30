export interface OHLCV {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface MAPoint {
  time: number;
  value: number;
}

export interface MASet {
  ma5: MAPoint[];
  ma20: MAPoint[];
  ma60: MAPoint[];
}

export interface ChartData {
  code: string;
  name: string;
  timeframe: "weekly" | "daily";
  candles: OHLCV[];
  ma: MASet;
}

export type ConditionKey =
  | "jump_dai"
  | "kahanshin"
  | "ppp_pullback"
  | "weekly_ma20_bounce"
  | "n_shape"
  | "dow_long_reversal"
  | "reverse_jump_dai"
  | "reverse_kahanshin"
  | "try_todokazu"
  | "dead_cross"
  | "golden_cross_imminent";

export const LONG_CONDITIONS: ConditionKey[] = [
  "jump_dai",
  "kahanshin",
  "ppp_pullback",
  "weekly_ma20_bounce",
  "n_shape",
  "dow_long_reversal",
  "golden_cross_imminent",
];

export const SHORT_CONDITIONS: ConditionKey[] = [
  "reverse_jump_dai",
  "reverse_kahanshin",
  "try_todokazu",
  "dead_cross",
];

export const CONDITION_LABELS: Record<ConditionKey, string> = {
  jump_dai: "ジャンプ台",
  kahanshin: "下半身",
  ppp_pullback: "PPP押し目",
  weekly_ma20_bounce: "週足20線反発",
  n_shape: "N大",
  dow_long_reversal: "ダウ転換(買)",
  reverse_jump_dai: "逆ジャンプ台",
  reverse_kahanshin: "逆下半身",
  try_todokazu: "トライ届かず",
  dead_cross: "デッドクロス",
  golden_cross_imminent: "GC直前",
};

export interface MASnapshot {
  ma5: number;
  ma20: number;
  ma60: number;
}

export interface CorporateEvents {
  earnings_near: boolean;
  earnings_days_until: number | null;
  earnings_revision_up: boolean;
  earnings_revision_down: boolean;
  warrant: boolean;
  secondary_offer: boolean;
  buyback: boolean;
}

export interface IndexCorrelation {
  index_name: string;
  beta: number;
  correlation: number;
  label: "指数連動型" | "独自動き型" | "逆相関型";
  beta_label: string | null;
}

export interface ScreenHit {
  code: string;
  name: string;
  segment: "Prime" | "Growth";
  last_price: number;
  last_volume: number;
  avg_weekly_volume: number;
  conditions_matched: ConditionKey[];
  signal_type: "long" | "short" | "mixed";
  weekly_ma: MASnapshot;
  daily_ma: MASnapshot;
  corporate_events: CorporateEvents;
  index_correlation: IndexCorrelation | null;
  volume_ratio: number | null;
  rs_score: number | null;
  signal_freshness_weeks: number | null;
}

export interface ScreenRequest {
  conditions: ConditionKey[];
  min_volume: number;
  max_price: number;
  segments: ("Prime" | "Growth")[];
}

export interface ConditionStat {
  win_rate: number | null;
  n: number | null;
  source: "backtest" | "lookup";
}

export interface MarketEnvironment {
  status: "bull" | "bear" | "neutral";
  topix_above_ma20: boolean;
  topix_ma5_above_ma20: boolean;
  description: string;
}

export interface ScreenResponse {
  screened_at: string;
  total_universe: number;
  hits: ScreenHit[];
  duration_ms: number;
  lookup_stats: Record<string, ConditionStat>;
  market_env: MarketEnvironment | null;
}
