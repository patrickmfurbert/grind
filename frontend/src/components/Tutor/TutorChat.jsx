import { useTutor } from "../../hooks/useTutor";
import TutorMessage from "./TutorMessage";
import TutorInput from "./TutorInput";

/** Socratic dialogue interface for a concept: streams tutor replies, lets the learner
 * respond, and restores/persists the conversation so it survives leaving the Study page. */
function TutorChat({ concept }) {
  const { messages, send, streaming, loadingHistory, clearHistory } = useTutor(concept.id);
  const opener = { role: "assistant", content: `Let's start with why ${concept.title} exists. What problem do you think it solves?` };
  const thread = messages.length ? messages : [opener];

  if (loadingHistory) {
    return (
      <div className="tutor-chat">
        <p className="tutor-loading">Loading conversation…</p>
      </div>
    );
  }

  return (
    <div className="tutor-chat">
      <div className="chat">
        {thread.map((message, index) => (
          <TutorMessage key={index} role={message.role} content={message.content} />
        ))}
      </div>
      <TutorInput onSend={send} disabled={streaming} />
      <button type="button" className="link-button start-fresh" onClick={clearHistory} disabled={streaming}>
        Start fresh
      </button>
    </div>
  );
}

export default TutorChat;

