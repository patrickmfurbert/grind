import { renderHook, waitFor } from "@testing-library/react";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useQuiz } from "./useQuiz";

function jsonResponse(body) {
  return { ok: true, json: async () => body };
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useQuiz", () => {
  it("generate populates questions and clears any prior result", async () => {
    const questions = [{ id: "q1", type: "comprehension", prompt: "Why?" }];
    global.fetch = vi.fn().mockResolvedValue(jsonResponse({ questions }));

    const { result } = renderHook(() => useQuiz("cap-theorem"));
    await act(async () => {
      await result.current.generate("comprehension");
    });

    expect(result.current.questions).toEqual(questions);
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/quiz/generate",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ concept_id: "cap-theorem", quiz_type: "comprehension", use_book_rag: false }),
      })
    );
  });

  it("sets generating to true while the request is in flight and false once resolved", async () => {
    const questions = [{ id: "q1", type: "comprehension", prompt: "Why?" }];
    let resolveFetch;
    global.fetch = vi.fn(() => new Promise((resolve) => { resolveFetch = resolve; }));

    const { result } = renderHook(() => useQuiz("cap-theorem"));
    act(() => {
      result.current.generate("comprehension");
    });
    await waitFor(() => expect(result.current.generating).toBe(true));

    await act(async () => {
      resolveFetch(jsonResponse({ questions }));
    });
    await waitFor(() => expect(result.current.generating).toBe(false));
  });

  it("submit posts the answer and stores the result", async () => {
    const submission = { correct: true, explanation: "Good.", next_review_date: "2026-01-01T00:00:00Z" };
    global.fetch = vi.fn().mockResolvedValue(jsonResponse(submission));

    const { result } = renderHook(() => useQuiz("cap-theorem"));
    await act(async () => {
      const returned = await result.current.submit("q1", "my answer", "comprehension");
      expect(returned).toEqual(submission);
    });

    await waitFor(() => expect(result.current.result).toEqual(submission));
    expect(result.current.grading).toBe(false);
  });
});
