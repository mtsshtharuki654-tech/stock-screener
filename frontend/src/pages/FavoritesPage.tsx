import { Link } from "react-router-dom";
import ResultsTable from "../components/screener/ResultsTable";
import { useFavorites } from "../hooks/useFavorites";
import { getCachedScreenResult } from "../hooks/useScreener";

export default function FavoritesPage() {
  const { favorites, toggleFavorite } = useFavorites();
  const result = getCachedScreenResult();

  const favoriteResult = result
    ? {
        ...result,
        hits: result.hits.filter((hit) => favorites.includes(hit.code)),
      }
    : null;

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-gray-950 text-white">
      <header className="flex items-center justify-between border-b border-gray-800 bg-gray-900/80 px-4 py-3">
        <div className="flex items-center gap-3">
          <Link to="/" className="text-sm text-blue-400 hover:text-blue-300">
            ← スクリーンに戻る
          </Link>
          <div>
            <h1 className="text-lg font-semibold">お気に入り一覧</h1>
            <p className="text-xs text-gray-500">登録済みの銘柄だけを表示しています</p>
          </div>
        </div>
        <div className="text-sm text-gray-400">
          お気に入り {favorites.length}件
        </div>
      </header>

      <ResultsTable
        result={favoriteResult}
        isLoading={false}
        progress=""
        pct={100}
        elapsed={0}
        eta={null}
        error={null}
        favoritesOnly={true}
        favoriteCodes={favorites}
        showRemoveButtons={true}
        onRemoveFavorite={(code) => toggleFavorite(code)}
      />
    </div>
  );
}
