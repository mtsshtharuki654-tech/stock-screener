import { BrowserRouter, Routes, Route } from "react-router-dom";
import ScreenerPage from "./pages/ScreenerPage";
import StockDetailPage from "./pages/StockDetailPage";
import FavoritesPage from "./pages/FavoritesPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ScreenerPage />} />
        <Route path="/favorites" element={<FavoritesPage />} />
        <Route path="/stock/:code" element={<StockDetailPage />} />
      </Routes>
    </BrowserRouter>
  );
}
