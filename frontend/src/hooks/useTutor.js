import { useCallback, useState } from "react";

/** Streams a Socratic tutor reply for a concept via SSE and appends tokens as they arrive. */
export function useTutor(conceptId) {
  const [messages, setMessages] = useState([]);
  const [streaming, setStreaming] = useState(false);

  const send = useCallback(
    async (message) => {
      const history = messages.map(({ role, content }) => ({ role, content }));
      setMessages((items) => [...items, { role: "user", content: message }, { role: "assistant", content: "" }]);
      setStreaming(true);
      try {
        const response = await fetch("/api/tutor/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ concept_id: conceptId, message, conversation_history: history }),
        });
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let text = "";
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          for (const line of decoder.decode(value).split("\n")) {
            if (!line.startsWith("data: ") || line === "data: [DONE]") continue;
            text += JSON.parse(line.slice(6)).token;
            setMessages((items) => [...items.slice(0, -1), { role: "assistant", content: text }]);
          }
        }
      } finally {
        setStreaming(false);
      }
    },
    [conceptId, messages]
  );

  return { messages, send, streaming };
}
