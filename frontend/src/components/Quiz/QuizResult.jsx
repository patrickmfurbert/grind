/** Shows whether the last quiz answer was correct, an explanation, the specific gap the
 * LLM identified (for free-response questions), and the next spaced-repetition date. */
function QuizResult({ result }) {
  if (!result) return null;
  return (
    <div className={`quiz-result ${result.correct ? "correct" : "incorrect"}`}>
      <strong>{result.correct ? "On track" : "Review needed"}</strong>
      <p>{result.explanation}</p>
      {result.gap && <p className="quiz-gap">🎯 Focus on: {result.gap}</p>}
      <small>
        Score: {result.score}/5 · Mastery: {result.mastery_level}/5 · Next review: {new Date(result.next_review_date).toLocaleDateString()}
      </small>
    </div>
  );
}

export default QuizResult;
