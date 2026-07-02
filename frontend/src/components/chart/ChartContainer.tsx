import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  type IChartApi,
  type ISeriesApi,
} from "lightweight-charts";
import type { ChartData } from "../../types";

interface Props {
  data: ChartData;
  showCandles: boolean;
  height?: number;
}

const CHART_BG = "#0a0a0f";
const GRID_COLOR = "#1e2030";

export default function ChartContainer({ data, showCandles, height = 420 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const ma5Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const ma20Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const ma60Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const volRef = useRef<ISeriesApi<"Histogram"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: CHART_BG },
        textColor: "#9ca3af",
      },
      grid: {
        vertLines: { color: GRID_COLOR },
        horzLines: { color: GRID_COLOR },
      },
      width: containerRef.current.clientWidth,
      height,
      timeScale: { borderColor: GRID_COLOR, timeVisible: true },
      rightPriceScale: { borderColor: GRID_COLOR },
    });

    const candle = chart.addCandlestickSeries({
      upColor:        "#ef4444",   // 陽線（赤）
      downColor:      "#22c55e",   // 陰線（緑）
      borderUpColor:  "#ef4444",
      borderDownColor:"#22c55e",
      wickUpColor:    "#ef4444",
      wickDownColor:  "#22c55e",
    });

    const ma5 = chart.addLineSeries({
      color: "#3b82f6",   // 青
      lineWidth: 2,
      priceLineVisible: false,
    });
    const ma20 = chart.addLineSeries({
      color: "#f97316",   // オレンジ
      lineWidth: 2,
      priceLineVisible: false,
    });
    const ma60 = chart.addLineSeries({
      color: "#a855f7",   // 紫（陰線の赤と区別）
      lineWidth: 2,
      priceLineVisible: false,
    });

    const vol = chart.addHistogramSeries({
      color: "#374151",
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    chart.priceScale("volume").applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
    });

    chartRef.current = chart;
    candleRef.current = candle;
    ma5Ref.current = ma5;
    ma20Ref.current = ma20;
    ma60Ref.current = ma60;
    volRef.current = vol;

    const observer = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
    };
  }, [height]);

  // データ更新
  useEffect(() => {
    if (!candleRef.current || !ma5Ref.current) return;

    candleRef.current.setData(
      data.candles.map((c) => ({
        time: c.time as unknown as string,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }))
    );

    ma5Ref.current.setData(
      data.ma.ma5.map((p) => ({ time: p.time as unknown as string, value: p.value }))
    );
    ma20Ref.current!.setData(
      data.ma.ma20.map((p) => ({ time: p.time as unknown as string, value: p.value }))
    );
    ma60Ref.current!.setData(
      data.ma.ma60.map((p) => ({ time: p.time as unknown as string, value: p.value }))
    );

    volRef.current!.setData(
      data.candles.map((c) => ({
        time: c.time as unknown as string,
        value: c.volume,
        color: c.close >= c.open ? "#ef444444" : "#22c55e44",
      }))
    );

    chartRef.current?.timeScale().fitContent();
  }, [data]);

  // 裸チャートトグル
  useEffect(() => {
    if (!candleRef.current) return;
    candleRef.current.applyOptions({ visible: showCandles });
    const width = (showCandles ? 2 : 3) as 1 | 2 | 3 | 4;
    ma5Ref.current?.applyOptions({ lineWidth: width });
    ma20Ref.current?.applyOptions({ lineWidth: width });
    ma60Ref.current?.applyOptions({ lineWidth: width });
  }, [showCandles]);

  return <div ref={containerRef} className="w-full" style={{ height }} />;
}
