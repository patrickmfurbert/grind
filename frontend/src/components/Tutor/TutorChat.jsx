import { useEffect, useRef, useState } from "react";
import { useTutor } from "../../hooks/useTutor";
import TutorMessage from "./TutorMessage";
import TutorInput from "./TutorInput";

const OPENERS = {
  learn: (title) => `Let's start with why ${title} exists. What problem do you think it solves?`,
  // Teach-back flips the roles (protege effect): the learner explains the concept first,
  // and the tutor only probes/critiques rather than teaching it.
  teach_back: (title) => `Teach me ${title} as if I'm a student who's never heard of it. I'll ask questions to find the gaps.`,
};

/** Socratic dialogue interface for a concept: streams tutor replies, lets the learner
 * respond, and restores/persists the conversation so it survives leaving the Study page.
 * Supports a "teach-back" mode where the learner explains the concept and the tutor
 * probes for gaps instead of explaining it. */
function TutorChat({ concept }) {
  const { messages, send, streaming, loadingHistory, clearHistory, masteryUpdate } = useTutor(concept.id);
  const [mode, setMode] = useState("learn");
  const chatRef = useRef(null);
  const opener = { role: "assistant", content: OPENERS[mode](concept.title) };
  const thread = messages.length ? messages : [opener];

  // Keep the newest message in view — both right after sending, and continuously as
  // the assistant's reply streams in token by token — instead of leaving the learner
  // scrolled up past it (or having to scroll down themselves) each turn.
  useEffect(() => {
    const node = chatRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [thread]);

  if (loadingHistory) {
    return (
      <div className="tutor-chat">
        <p className="tutor-loading">Loading conversation…</p>
      </div>
    );
  }

  return (
    <div className="tutor-chat">
      <div className="tutor-mode-toggle">
        <button type="button" className={mode === "learn" ? "active" : ""} onClick={() => setMode("learn")} disabled={streaming}>
          Learn
        </button>
        <button type="button" className={mode === "teach_back" ? "active" : ""} onClick={() => setMode("teach_back")} disabled={streaming}>
          Teach it back
        </button>
      </div>
      <div className="chat" ref={chatRef}>
        {thread.map((message, index) => (
          <TutorMessage key={index} role={message.role} content={message.content} sources={message.sources} />
        ))}
        {masteryUpdate && (
          <p className="mastery-update-note">📈 Mastery updated to {masteryUpdate.level}/5 based on your explanation.</p>
        )}
      </div>
      <TutorInput onSend={(message) => send(message, mode)} disabled={streaming} />
      <button type="button" className="link-button start-fresh" onClick={clearHistory} disabled={streaming}>
        Start fresh
      </button>
    </div>
  );
}

export default TutorChat;
