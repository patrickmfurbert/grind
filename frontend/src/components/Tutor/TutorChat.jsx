import { useTutor } from "../../hooks/useTutor";
import TutorMessage from "./TutorMessage";
import TutorInput from "./TutorInput";

/** Socratic dialogue interface for a concept: streams tutor replies and lets the learner respond. */
function TutorChat({ concept }) {
  const { messages, send, streaming } = useTutor(concept.id);
  const opener = { role: "assistant", content: `Let's start with why ${concept.title} exists. What problem do you think it solves?` };
  const thread = messages.length ? messages : [opener];

  return (
    <div className="tutor-chat">
      <div className="chat">
        {thread.map((message, index) => (
          <TutorMessage key={index} role={message.role} content={message.content} />
        ))}
      </div>
      <TutorInput onSend={send} disabled={streaming} />
    </div>
  );
}

export default TutorChat;
