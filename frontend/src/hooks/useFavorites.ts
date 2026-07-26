import { useEffect, useState, useCallback } from "react";

const STORAGE_KEY = "favorites_stocks";

function readFavorites(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((v): v is string => typeof v === "string") : [];
  } catch {
    return [];
  }
}

function writeFavorites(codes: string[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(codes));
  } catch {
    // ignore
  }
}

export function useFavorites() {
  const [favorites, setFavorites] = useState<string[]>(() => readFavorites());

  useEffect(() => {
    writeFavorites(favorites);
  }, [favorites]);

  const toggleFavorite = useCallback((code: string) => {
    setFavorites((prev) => {
      if (prev.includes(code)) {
        return prev.filter((item) => item !== code);
      }
      return [...prev, code];
    });
  }, []);

  const isFavorite = useCallback((code: string) => favorites.includes(code), [favorites]);

  return { favorites, toggleFavorite, isFavorite };
}
