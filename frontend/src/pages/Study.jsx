import { useNavigate } from "react-router-dom";
import TutorChat from "../components/Tutor/TutorChat";
import NoConceptSelected from "../components/NoConceptSelected";
import { useStore } from "../store";

/** Active study session: Socratic tutor chat scoped to the currently selected concept. */
function Study() {
  const { activeConcept } = useStore();
  const navigate = useNavigate();

  if (!activeConcept) return <NoConceptSelected verb="study" />;

  return (
    <section className="study">
      <p className="eyebrow">{activeConcept.phase}</p>
      <h1>{activeConcept.title}</h1>
      <p>{activeConcept.description}</p>
      <nav className="study-nav">
        <button onClick={() => navigate("/quiz")}>Quiz me</button>
        <button onClick={() => navigate("/code")}>Code lab</button>
      </nav>
      <TutorChat concept={activeConcept} key={activeConcept.id} />
    </section>
  );
}

export default Study;
