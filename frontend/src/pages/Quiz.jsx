import { useEffect, useState } from "react";
import QuizCard from "../components/Quiz/QuizCard";
import QuizResult from "../components/Quiz/QuizResult";
import SpacedRepetition from "../components/Quiz/SpacedRepetition";
import NoConceptSelected from "../components/NoConceptSelected";
import { useQuiz } from "../hooks/useQuiz";
import { useStore } from "../store";

const QUIZ_TYPES = ["comprehension", "application", "connection"];

/** Quiz mode: comprehension/application/connection questions for a concept, plus today's due queue. */
function Quiz() {
  const { activeConcept, setActiveConcept } = useStore();
  const [quizType, setQuizType] = useState("comprehension");
  const { questions, result, error, generating, grading, generate, submit, getHint } = useQuiz(activeConcept?.id);
  const quizTypes = activeConcept?.phase === "Phase 6" ? [...QUIZ_TYPES, "pattern_recognition"] : QUIZ_TYPES;

  useEffect(() => {
    if (activeConcept) generate(quizType);
  }, [activeConcept, quizType, generate]);

  if (!activeConcept) return <NoConceptSelected verb="quiz" />;

  return (
    <section className="quiz">
      <h1>{activeConcept.title}</h1>
      <div className="quiz-types">
        {quizTypes.map((type) => (
          <button key={type} className={type === quizType ? "active" : ""} onClick={() => setQuizType(type)}>
            {type.replace("_", " ")}
          </button>
        ))}
      </div>
      {error && <p className="upload-error">{error}</p>}
      {generating && <p className="quiz-generating">Generating questions…</p>}
      {!generating &&
        questions.map((question) => (
          <QuizCard
            key={question.id}
            question={question}
            isInterleaved={question.concept_id !== activeConcept.id}
            grading={grading}
            onSubmit={(questionId, answer) => submit(questionId, answer)}
            onGetHint={getHint}
          />
        ))}
      <QuizResult result={result} />
      <SpacedRepetition onSelect={setActiveConcept} />
    </section>
  );
}

export default Quiz;
