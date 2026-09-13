import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
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
  const navigate = useNavigate();
  const [quizType, setQuizType] = useState("comprehension");
  const { questions, result, generate, submit } = useQuiz(activeConcept?.id);

  useEffect(() => {
    if (activeConcept) generate(quizType);
  }, [activeConcept, quizType, generate]);

  if (!activeConcept) return <NoConceptSelected verb="quiz" />;

  return (
    <section className="quiz">
      <button className="back" onClick={() => navigate("/study")}>
        ← Study
      </button>
      <h1>{activeConcept.title}</h1>
      <div className="quiz-types">
        {QUIZ_TYPES.map((type) => (
          <button key={type} className={type === quizType ? "active" : ""} onClick={() => setQuizType(type)}>
            {type}
          </button>
        ))}
      </div>
      {questions.map((question) => (
        <QuizCard key={question.id} question={question} onSubmit={submit} />
      ))}
      <QuizResult result={result} />
      <SpacedRepetition onSelect={setActiveConcept} />
    </section>
  );
}

export default Quiz;
