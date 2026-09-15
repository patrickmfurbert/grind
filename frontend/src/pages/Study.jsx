import TutorChat from "../components/Tutor/TutorChat";
import NoConceptSelected from "../components/NoConceptSelected";
import { useStore } from "../store";

/** Active study session: Socratic tutor chat scoped to the currently selected concept. */
function Study() {
  const { activeConcept } = useStore();

  if (!activeConcept) return <NoConceptSelected verb="study" />;

  return (
    <section className="study">
      <p className="eyebrow">{activeConcept.phase}</p>
      <h1>{activeConcept.title}</h1>
      <p>{activeConcept.description}</p>
      <TutorChat concept={activeConcept} key={activeConcept.id} />
    </section>
  );
}

export default Study;
