import { useState } from "react";

/** A single quiz question with a free-response answer and a 0-5 self-assessed score for SM-2. */
function QuizCard({ question, onSubmit }) {
  const [answer, setAnswer] = useState("");
  const [score, setScore] = useState(3);

  function submit(event) {
    event.preventDefault();
    onSubmit(question.id, answer, question.type, score);
  }

  return (
    <form className="quiz-card" onSubmit={submit}>
      <p className="prompt">{question.prompt}</p>
      <textarea value={answer} onChange={(event) => setAnswer(event.target.value)} placeholder="Your answer..." rows={4} />
      <label>
        Confidence
        <input type="range" min={0} max={5} value={score} onChange={(event) => setScore(Number(event.target.value))} />
        <span>{score}/5</span>
      </label>
      <button>Submit</button>
    </form>
  );
}

export default QuizCard;
