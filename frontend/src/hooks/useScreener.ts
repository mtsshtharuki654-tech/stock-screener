import { useMutation } from "@tanstack/react-query";
import { runScreen } from "../api/client";
import type { ScreenRequest, ScreenResponse } from "../types";

export function useScreener() {
  return useMutation<ScreenResponse, Error, ScreenRequest>({
    mutationFn: runScreen,
  });
}
