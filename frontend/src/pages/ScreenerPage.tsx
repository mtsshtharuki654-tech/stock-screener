import { useScreener } from "../hooks/useScreener";
import ScreenerPanel from "../components/screener/ScreenerPanel";
import ResultsTable from "../components/screener/ResultsTable";

export default function ScreenerPage() {
  const { mutate, data, isPending, progress, error } = useScreener();

  return (
    <div className="flex h-screen overflow-hidden">
      <ScreenerPanel onRun={mutate} isLoading={isPending} />
      <main className="flex-1 flex flex-col overflow-hidden">
        <ResultsTable result={data ?? null} isLoading={isPending} progress={progress} error={error} />
      </main>
    </div>
  );
}
