import { useNavigate } from "react-router-dom";
import type { ScreenHit, ScreenResponse } from "../../types";
import ResultRow from "./ResultRow";

interface Props {
  result: ScreenResponse | null;
  isLoading: boolean;
  error: Error | null;
}

const HEADERS = [
  "コード", "銘柄名", "株価", "直近出来高", "週平均出来高",
  "シグナル", "ヒット条件", "注意情報", "指数連動性",
];

export default function ResultsTable({ result, isLoading, error }: Props) {
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl mb-4 animate-spin">⟳</div>
          <p className="text-gray-300 font-medium">スクリーニング中...</p>
          <p className="text-gray-500 text-sm mt-2">初回はJ-Quantsからデータを取得するため<br />数分かかる場合があります。そのままお待ちください。</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center text-red-400">
          <p className="text-xl mb-2">エラーが発生しました</p>
          <p className="text-sm text-gray-500">{error.message}</p>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-600">
        <div className="text-center">
          <p className="text-2xl mb-2">条件を設定してスクリーニングを実行してください</p>
          <p className="text-sm">左パネルで条件を選択し、「スクリーニング実行」ボタンを押してください</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* サマリー */}
      <div className="px-4 py-2 bg-gray-900 border-b border-gray-800 flex items-center gap-4 text-sm text-gray-400">
        <span>ユニバース: <strong className="text-white">{result.total_universe.toLocaleString()}</strong> 銘柄</span>
        <span>ヒット: <strong className="text-blue-400">{result.hits.length}</strong> 銘柄</span>
        <span>処理時間: {(result.duration_ms / 1000).toFixed(1)}秒</span>
        <span className="ml-auto text-xs">{new Date(result.screened_at).toLocaleString("ja-JP")}</span>
      </div>

      {result.hits.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-gray-600">
          <p>条件にヒットする銘柄が見つかりませんでした</p>
        </div>
      ) : (
        <div className="flex-1 overflow-auto">
          <table className="w-full text-left text-gray-100 min-w-max">
            <thead className="bg-gray-900 sticky top-0">
              <tr>
                {HEADERS.map((h) => (
                  <th key={h} className="px-3 py-2 text-xs text-gray-400 font-semibold uppercase whitespace-nowrap border-b border-gray-800">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.hits.map((hit) => (
                <ResultRow
                  key={hit.code}
                  hit={hit}
                  onClick={() => navigate(`/stock/${hit.code}`, { state: { hit } })}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
