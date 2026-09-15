import { useCallback, useState } from "react";
import { api } from "./api";

/** Fetches quiz questions for a concept and submits answers for grading + spaced-repetition scheduling. */
export function useQuiz(conceptId) {
  const [questions, setQuestions] = useState([]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);
  const [grading, setGrading] = useState(false);

  const generate = useCallback(
    async (quizType, useBookRag = false) => {
      setError("");
      setGenerating(true);
      try {
        const data = await api("/quiz/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ concept_id: conceptId, quiz_type: quizType, use_book_rag: useBookRag }),
        });
        setQuestions(data.questions);
        setResult(null);
      } catch {
        setQuestions([]);
        setError("Couldn't generate questions right now. Please try again.");
      } finally {
        setGenerating(false);
      }
    },
    [conceptId]
  );

  const submit = useCallback(async (questionId, answer) => {
    setError("");
    setGrading(true);
    try {
      const data = await api("/quiz/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question_id: questionId, answer }),
      });
      setResult(data);
      return data;
    } catch {
      setError("Couldn't grade that answer right now. Please try again.");
      return null;
    } finally {
      setGrading(false);
    }
  }, []);

  // Fetches a scaffolded hint for a free-response question (nudges without revealing
  // the answer). Best-effort: returns null on failure rather than surfacing a hard error.
  const getHint = useCallback(async (questionId) => {
    try {
      const data = await api("/quiz/hint", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question_id: questionId }),
      });
      return data.hint;
    } catch {
      return null;
    }
  }, []);

  return { questions, result, error, generating, grading, generate, submit, getHint };
}
