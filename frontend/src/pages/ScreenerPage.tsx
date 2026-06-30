import { useScreener } from "../hooks/useScreener";
import ScreenerPanel from "../components/screener/ScreenerPanel";
import ResultsTable from "../components/screener/ResultsTable";

export default function ScreenerPage() {
  const { mutate, clearResult, data, isFromCache, isPending, progress, pct, elapsed, eta, error } = useScreener();

  return (
    <div className="flex h-screen overflow-hidden">
      <ScreenerPanel onRun={mutate} isLoading={isPending} />
      <main className="flex-1 flex flex-col overflow-hidden">
        <ResultsTable
          result={data ?? null}
          isFromCache={isFromCache}
          onClear={clearResult}
          isLoading={isPending}
          progress={progress}
          pct={pct}
          elapsed={elapsed}
          eta={eta}
          error={error}
        />
      </main>
    </div>
  );
}
