import { useState } from "react";
import { Link } from "react-router-dom";
import { useScreener } from "../hooks/useScreener";
import ScreenerPanel from "../components/screener/ScreenerPanel";
import ResultsTable from "../components/screener/ResultsTable";
import { useFavorites } from "../hooks/useFavorites";

export default function ScreenerPage() {
  const { mutate, clearResult, data, isFromCache, isPending, progress, pct, elapsed, eta, error } = useScreener();
  const { favorites } = useFavorites();
  const [favoritesOnly, setFavoritesOnly] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden">
      <ScreenerPanel onRun={mutate} isLoading={isPending} />
      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="flex items-center justify-end gap-3 border-b border-gray-800 bg-gray-900/70 px-4 py-2">
          <button
            type="button"
            onClick={() => setFavoritesOnly((v) => !v)}
            className={`rounded px-2.5 py-1 text-sm ${favoritesOnly ? "bg-yellow-600 text-white" : "bg-gray-800 text-gray-300 hover:bg-gray-700"}`}
          >
            {favoritesOnly ? "★ お気に入りのみ" : "☆ お気に入りのみ"}
          </button>
          <Link to="/favorites" className="text-sm text-yellow-400 hover:text-yellow-300">
            お気に入り一覧 ({favorites.length})
          </Link>
        </div>
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
          favoritesOnly={favoritesOnly}
          favoriteCodes={favorites}
        />
      </main>
    </div>
  );
}
