import { useCallback, useState } from "react";
import { api } from "./api";

/** Fetches quiz questions for a concept and submits answers for SM-2 spaced-repetition scoring. */
export function useQuiz(conceptId) {
  const [questions, setQuestions] = useState([]);
  const [result, setResult] = useState(null);

  const generate = useCallback(
    async (quizType, useBookRag = false) => {
      const data = await api("/quiz/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ concept_id: conceptId, quiz_type: quizType, use_book_rag: useBookRag }),
      });
      setQuestions(data.questions);
      setResult(null);
    },
    [conceptId]
  );

  const submit = useCallback(
    async (questionId, answer, quizType, score) => {
      const data = await api("/quiz/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ concept_id: conceptId, question_id: questionId, answer, quiz_type: quizType, score }),
      });
      setResult(data);
      return data;
    },
    [conceptId]
  );

  return { questions, result, generate, submit };
}
