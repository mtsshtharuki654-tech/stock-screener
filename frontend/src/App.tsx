import { BrowserRouter, Routes, Route } from "react-router-dom";
import ScreenerPage from "./pages/ScreenerPage";
import StockDetailPage from "./pages/StockDetailPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ScreenerPage />} />
        <Route path="/stock/:code" element={<StockDetailPage />} />
      </Routes>
    </BrowserRouter>
  );
}
