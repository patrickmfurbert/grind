/** A single chat bubble for either the tutor (assistant) or the learner (user). */
function TutorMessage({ role, content }) {
  return <div className={`message ${role}`}>{content || (role === "assistant" ? "…" : "")}</div>;
}

export default TutorMessage;
