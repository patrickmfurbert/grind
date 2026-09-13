import { renderHook, waitFor } from "@testing-library/react";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useTutor } from "./useTutor";

function sseResponse(chunks) {
  const encoder = new TextEncoder();
  let index = 0;
  return {
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

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useTutor", () => {
  it("appends the user message immediately and streams tokens into the assistant reply", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      sseResponse([
        'data: {"token": "Why"}\n\n',
        'data: {"token": " it exists"}\n\n',
        "data: [DONE]\n\n",
      ])
    );

    const { result } = renderHook(() => useTutor("cap-theorem"));

    await act(async () => {
      await result.current.send("What is CAP theorem?");
    });

    expect(result.current.messages[0]).toEqual({ role: "user", content: "What is CAP theorem?" });
    await waitFor(() =>
      expect(result.current.messages[1]).toEqual({ role: "assistant", content: "Why it exists" })
    );
    expect(result.current.streaming).toBe(false);
  });

  it("sends concept_id and prior conversation history in the request body", async () => {
    global.fetch = vi.fn().mockResolvedValue(sseResponse(["data: [DONE]\n\n"]));

    const { result } = renderHook(() => useTutor("cap-theorem"));
    await act(async () => {
      await result.current.send("hello");
    });

    const [, options] = global.fetch.mock.calls[0];
    const body = JSON.parse(options.body);
    expect(body.concept_id).toBe("cap-theorem");
    expect(body.message).toBe("hello");
    expect(body.conversation_history).toEqual([]);
  });
});
