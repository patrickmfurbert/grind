import { useState } from "react";

/** A single quiz question: multiple_choice renders as radio options (instantly graded),
 * free_response renders as a textarea (graded by the evaluation LLM on submit).
 * isInterleaved tags questions mixed in from a different (weaker) concept, and
 * onGetHint (free_response only) requests a scaffolded, non-revealing hint. */
function QuizCard({ question, onSubmit, onGetHint, grading = false, isInterleaved = false }) {
  const [answer, setAnswer] = useState("");
  const [hint, setHint] = useState("");
  const [hintLoading, setHintLoading] = useState(false);
  const isMultipleChoice = question.type === "multiple_choice";

  function submit(event) {
    event.preventDefault();
    if (!answer || grading) return;
    onSubmit(question.id, answer);
  }

  async function requestHint() {
    if (!onGetHint || hintLoading) return;
    setHintLoading(true);
    const result = await onGetHint(question.id);
    setHint(result || "Couldn't get a hint right now. Please try again.");
    setHintLoading(false);
  }

  return (
    <form className="quiz-card" onSubmit={submit}>
      {isInterleaved && <span className="interleave-badge">🔀 {question.concept_title}</span>}
      <p className="prompt">{question.prompt}</p>
      {isMultipleChoice ? (
        <div className="quiz-options">
          {question.options.map((option) => (
            <label key={option} className={answer === option ? "selected" : ""}>
              <input type="radio" name={question.id} value={option} checked={answer === option} onChange={(event) => setAnswer(event.target.value)} />
              {option}
            </label>
          ))}
        </div>
      ) : (
        <>
          <textarea value={answer} onChange={(event) => setAnswer(event.target.value)} placeholder="Your answer..." rows={4} />
          {onGetHint && (
            <button type="button" className="link-button hint-button" onClick={requestHint} disabled={hintLoading}>
              {hintLoading ? "Thinking of a hint…" : "Need a hint?"}
            </button>
          )}
          {hint && <p className="quiz-hint">💡 {hint}</p>}
        </>
      )}
      <button disabled={!answer || grading}>{grading ? "Grading…" : "Submit"}</button>
    </form>
  );
}

export default QuizCard;
