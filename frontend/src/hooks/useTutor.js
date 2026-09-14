import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Streams a Socratic tutor reply for a concept via SSE, appends tokens as they arrive,
 * and persists/restores the conversation via the backend so it survives navigating
 * away from (and back to) the Study page instead of living only in this component's
 * state.
 */
export function useTutor(conceptId) {
  const [messages, setMessages] = useState([]);
  const [streaming, setStreaming] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const sessionIdRef = useRef(null);

  const loadHistory = useCallback(async () => {
    setLoadingHistory(true);
    try {
      const response = await fetch(`/api/tutor/history/${conceptId}`);
      const data = await response.json();
      sessionIdRef.current = data.session_id;
      setMessages(data.messages || []);
    } catch {
      sessionIdRef.current = null;
      setMessages([]);
    } finally {
      setLoadingHistory(false);
    }
  }, [conceptId]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const saveMessage = useCallback(
    (role, content) => {
      if (!sessionIdRef.current) return;
      fetch("/api/tutor/message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ concept_id: conceptId, session_id: sessionIdRef.current, role, content }),
      }).catch(() => {
        // Best-effort persistence: a failed save just means this turn won't be restored
        // next visit, but shouldn't interrupt the live conversation.
      });
    },
    [conceptId]
  );

  const send = useCallback(
    async (message) => {
      // Always sent as the full restored history (state was seeded from GET
      // /tutor/history on mount), so the tutor keeps context across visits.
      const history = messages.map(({ role, content }) => ({ role, content }));
      setMessages((items) => [...items, { role: "user", content: message }, { role: "assistant", content: "" }]);
      saveMessage("user", message);
      setStreaming(true);
      let finalText = "";
      let failed = false;
      let sources = [];
      try {
        const response = await fetch("/api/tutor/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ concept_id: conceptId, message, conversation_history: history }),
        });
        if (!response.ok) {
          throw new Error(`Tutor request failed (${response.status})`);
        }
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let text = "";
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          for (const line of decoder.decode(value).split("\n")) {
            if (!line.startsWith("data: ") || line === "data: [DONE]") continue;
            const payload = JSON.parse(line.slice(6));
            if (payload.error) {
              text = text ? `${text}\n\n⚠️ ${payload.error}` : `⚠️ ${payload.error}`;
            } else if (payload.sources) {
              sources = payload.sources;
              continue;
            } else {
              text += payload.token;
            }
            setMessages((items) => [...items.slice(0, -1), { role: "assistant", content: text, sources }]);
          }
        }
        finalText = text;
      } catch (err) {
        failed = true;
        finalText = `⚠️ ${err.message || "The tutor is unavailable right now. Please try again."}`;
        setMessages((items) => [...items.slice(0, -1), { role: "assistant", content: finalText }]);
      } finally {
        setStreaming(false);
        // Only persist a genuine reply. A request-level failure (network/connection
        // never got a response) isn't worth baking into permanent history.
        if (finalText && !failed) saveMessage("assistant", finalText);
      }
    },
    [conceptId, messages, saveMessage]
  );

  const clearHistory = useCallback(async () => {
    await fetch(`/api/tutor/history/${conceptId}`, { method: "DELETE" });
    await loadHistory();
  }, [conceptId, loadHistory]);

  return { messages, send, streaming, loadingHistory, clearHistory };
}


