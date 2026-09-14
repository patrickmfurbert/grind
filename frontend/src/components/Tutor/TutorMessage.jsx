import ReactMarkdown from "react-markdown";

/** A single chat bubble for either the tutor (assistant) or the learner (user).
 * Assistant replies render as markdown (code blocks, lists, etc.); user messages stay
 * plain text. Assistant replies grounded in uploaded books also show a citations list. */
function TutorMessage({ role, content, sources }) {
  return (
    <div className={`message ${role}`}>
      {role === "assistant" ? <ReactMarkdown>{content || "…"}</ReactMarkdown> : content}
      {sources && sources.length > 0 && (
        <ul className="message-sources">
          {sources.map((source) => (
            <li key={`${source.title}-${source.page}`}>
              📖 {source.title}, p. {source.page}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default TutorMessage;
