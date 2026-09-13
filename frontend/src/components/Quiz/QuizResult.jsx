/** Shows whether the last quiz answer was correct, an explanation, and the next spaced-repetition date. */
function QuizResult({ result }) {
  if (!result) return null;
  return (
    <div className={`quiz-result ${result.correct ? "correct" : "incorrect"}`}>
      <strong>{result.correct ? "On track" : "Review needed"}</strong>
      <p>{result.explanation}</p>
      <small>Next review: {new Date(result.next_review_date).toLocaleDateString()}</small>
    </div>
  );
}

export default QuizResult;
