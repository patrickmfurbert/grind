import { useState } from "react";

/** A single quiz question: multiple_choice renders as radio options (instantly graded),
 * free_response renders as a textarea (graded by the evaluation LLM on submit). */
function QuizCard({ question, onSubmit, grading = false }) {
  const [answer, setAnswer] = useState("");
  const isMultipleChoice = question.type === "multiple_choice";

  function submit(event) {
    event.preventDefault();
    if (!answer || grading) return;
    onSubmit(question.id, answer);
  }

  return (
    <form className="quiz-card" onSubmit={submit}>
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
        <textarea value={answer} onChange={(event) => setAnswer(event.target.value)} placeholder="Your answer..." rows={4} />
      )}
      <button disabled={!answer || grading}>{grading ? "Grading…" : "Submit"}</button>
    </form>
  );
}

export default QuizCard;
