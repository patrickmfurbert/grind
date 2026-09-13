import { renderHook, waitFor } from "@testing-library/react";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useProgress } from "./useProgress";

function jsonResponse(body) {
  return { ok: true, json: async () => body };
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useProgress", () => {
  it("loads the summary on mount", async () => {
    const summary = { overall_pct: 10, streak: 1, by_phase: [] };
    global.fetch = vi.fn().mockResolvedValue(jsonResponse(summary));

    const { result } = renderHook(() => useProgress());

    await waitFor(() => expect(result.current.summary).toEqual(summary));
    expect(global.fetch).toHaveBeenCalledWith("/api/progress/summary", undefined);
  });

  it("setMastery posts the update then refreshes the summary", async () => {
    const summary = { overall_pct: 20, streak: 2, by_phase: [] };
    global.fetch = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ overall_pct: 0, streak: 0, by_phase: [] }))
      .mockResolvedValueOnce(jsonResponse({ updated: true }))
      .mockResolvedValueOnce(jsonResponse(summary));

    const { result } = renderHook(() => useProgress());
    await waitFor(() => expect(result.current.summary).not.toBeNull());

    await act(async () => {
      await result.current.setMastery("cap-theorem", 3);
    });

    expect(global.fetch).toHaveBeenNthCalledWith(
      2,
      "/api/progress/mastery",
      expect.objectContaining({ method: "POST" })
    );
    expect(result.current.summary).toEqual(summary);
  });
});
