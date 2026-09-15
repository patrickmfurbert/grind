import { renderHook, waitFor } from "@testing-library/react";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useTutor } from "./useTutor";

function sseResponse(chunks, options = {}) {
  const { ok = true, status = 200 } = options;
  const encoder = new TextEncoder();
  let index = 0;
  return {
    ok,
    status,
    body: {
      getReader() {
        return {
          async read() {
            if (index >= chunks.length) return { done: true, value: undefined };
            const value = encoder.encode(chunks[index]);
            index += 1;
            return { done: false, value };
          },
        };
      },
    },
  };
}

function historyResponse(sessionId, messages = []) {
  return { ok: true, json: async () => ({ session_id: sessionId, messages }) };
}

/** Routes fetch calls by URL/method so history/message persistence calls (fired
 * automatically on mount and after every turn) don't need to be mocked individually
 * in every test — only the interesting ones are asserted on directly. */
function mockFetchRouter({ history = historyResponse("session-1"), chat = sseResponse(["data: [DONE]\n\n"]) } = {}) {
  return vi.fn(async (url, options = {}) => {
    if (typeof url === "string" && url.includes("/tutor/history/")) {
      if (options.method === "DELETE") return { ok: true, json: async () => ({ cleared: true }) };
      return history;
    }
    if (typeof url === "string" && url.includes("/tutor/message")) {
      return { ok: true, json: async () => ({ saved: true }) };
    }
    return chat;
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useTutor", () => {
  it("restores prior conversation history on mount and stops loading", async () => {
    global.fetch = mockFetchRouter({
      history: historyResponse("session-1", [{ role: "user", content: "hi" }, { role: "assistant", content: "hello" }]),
    });

    const { result } = renderHook(() => useTutor("cap-theorem"));

    expect(result.current.loadingHistory).toBe(true);
    await waitFor(() => expect(result.current.loadingHistory).toBe(false));
    expect(result.current.messages).toEqual([
      { role: "user", content: "hi" },
      { role: "assistant", content: "hello" },
    ]);
  });

  it("appends the user message immediately and streams tokens into the assistant reply", async () => {
    global.fetch = mockFetchRouter({
      chat: sseResponse(['data: {"token": "Why"}\n\n', 'data: {"token": " it exists"}\n\n', "data: [DONE]\n\n"]),
    });

    const { result } = renderHook(() => useTutor("cap-theorem"));
    await waitFor(() => expect(result.current.loadingHistory).toBe(false));

    await act(async () => {
      await result.current.send("What is CAP theorem?");
    });

    expect(result.current.messages[0]).toEqual({ role: "user", content: "What is CAP theorem?" });
    await waitFor(() =>
      expect(result.current.messages[1]).toEqual({ role: "assistant", content: "Why it exists", sources: [] })
    );
    expect(result.current.streaming).toBe(false);
  });

  it("attaches book citations from the sources SSE event to the assistant reply", async () => {
    global.fetch = mockFetchRouter({
      chat: sseResponse([
        'data: {"token": "CAP stands for..."}\n\n',
        'data: {"sources": [{"title": "Designing Data-Intensive Applications", "page": 42}]}\n\n',
        "data: [DONE]\n\n",
      ]),
    });

    const { result } = renderHook(() => useTutor("cap-theorem"));
    await waitFor(() => expect(result.current.loadingHistory).toBe(false));

    await act(async () => {
      await result.current.send("What is CAP theorem?");
    });

    await waitFor(() =>
      expect(result.current.messages[1]).toEqual({
        role: "assistant",
        content: "CAP stands for...",
        sources: [{ title: "Designing Data-Intensive Applications", page: 42 }],
      })
    );
  });

  it("sends concept_id and prior conversation history in the request body", async () => {
    global.fetch = mockFetchRouter();

    const { result } = renderHook(() => useTutor("cap-theorem"));
    await waitFor(() => expect(result.current.loadingHistory).toBe(false));
    await act(async () => {
      await result.current.send("hello");
    });

    const chatCall = global.fetch.mock.calls.find(([url]) => typeof url === "string" && url.includes("/tutor/chat"));
    const body = JSON.parse(chatCall[1].body);
    expect(body.concept_id).toBe("cap-theorem");
    expect(body.message).toBe("hello");
    expect(body.conversation_history).toEqual([]);
  });

  it("defaults to learn mode, and sends teach_back mode when passed to send", async () => {
    global.fetch = mockFetchRouter();

    const { result } = renderHook(() => useTutor("cap-theorem"));
    await waitFor(() => expect(result.current.loadingHistory).toBe(false));
    await act(async () => {
      await result.current.send("hello");
    });
    let chatCall = global.fetch.mock.calls.find(([url]) => typeof url === "string" && url.includes("/tutor/chat"));
    expect(JSON.parse(chatCall[1].body).mode).toBe("learn");

    global.fetch.mockClear();
    await act(async () => {
      await result.current.send("teach me this", "teach_back");
    });
    chatCall = global.fetch.mock.calls.find(([url]) => typeof url === "string" && url.includes("/tutor/chat"));
    expect(JSON.parse(chatCall[1].body).mode).toBe("teach_back");
  });

  it("persists both the user message and the assistant reply after a turn completes", async () => {
    global.fetch = mockFetchRouter({
      history: historyResponse("session-42"),
      chat: sseResponse(['data: {"token": "answer"}\n\n', "data: [DONE]\n\n"]),
    });

    const { result } = renderHook(() => useTutor("cap-theorem"));
    await waitFor(() => expect(result.current.loadingHistory).toBe(false));
    await act(async () => {
      await result.current.send("hello");
    });

    await waitFor(() => {
      const saveCalls = global.fetch.mock.calls.filter(([url]) => typeof url === "string" && url.includes("/tutor/message"));
      expect(saveCalls).toHaveLength(2);
    });
    const saveCalls = global.fetch.mock.calls.filter(([url]) => typeof url === "string" && url.includes("/tutor/message"));
    const [userSave, assistantSave] = saveCalls.map(([, options]) => JSON.parse(options.body));
    expect(userSave).toMatchObject({ concept_id: "cap-theorem", session_id: "session-42", role: "user", content: "hello" });
    expect(assistantSave).toMatchObject({ concept_id: "cap-theorem", session_id: "session-42", role: "assistant", content: "answer" });
  });

  it("renders a mid-stream error event as a warning in the assistant reply", async () => {
    global.fetch = mockFetchRouter({
      chat: sseResponse([
        'data: {"token": "Let\'s "}\n\n',
        'data: {"error": "The tutor is unavailable right now. Please try again."}\n\n',
        "data: [DONE]\n\n",
      ]),
    });

    const { result } = renderHook(() => useTutor("cap-theorem"));
    await waitFor(() => expect(result.current.loadingHistory).toBe(false));
    await act(async () => {
      await result.current.send("hello");
    });

    expect(result.current.messages[1].content).toContain("Let's");
    expect(result.current.messages[1].content).toContain("⚠️ The tutor is unavailable right now");
    expect(result.current.streaming).toBe(false);
  });

  it("renders an error when the request itself fails", async () => {
    global.fetch = mockFetchRouter({ chat: sseResponse([], { ok: false, status: 500 }) });

    const { result } = renderHook(() => useTutor("cap-theorem"));
    await waitFor(() => expect(result.current.loadingHistory).toBe(false));
    await act(async () => {
      await result.current.send("hello");
    });

    expect(result.current.messages[1].content).toContain("⚠️");
    expect(result.current.streaming).toBe(false);
  });

  it("clearHistory deletes and reloads a fresh (empty) session", async () => {
    let historyCallCount = 0;
    global.fetch = vi.fn(async (url, options = {}) => {
      if (typeof url === "string" && url.includes("/tutor/history/")) {
        if (options.method === "DELETE") return { ok: true, json: async () => ({ cleared: true }) };
        historyCallCount += 1;
        return historyCallCount === 1
          ? historyResponse("session-1", [{ role: "user", content: "old message" }])
          : historyResponse("session-2", []);
      }
      return { ok: true, json: async () => ({ saved: true }) };
    });

    const { result } = renderHook(() => useTutor("cap-theorem"));
    await waitFor(() => expect(result.current.messages).toEqual([{ role: "user", content: "old message" }]));

    await act(async () => {
      await result.current.clearHistory();
    });

    expect(result.current.messages).toEqual([]);
    const deleteCall = global.fetch.mock.calls.find(([, options]) => options?.method === "DELETE");
    expect(deleteCall[0]).toContain("/tutor/history/cap-theorem");
  });
});
