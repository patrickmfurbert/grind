import { Link } from "react-router-dom";
import SpacedRepetition from "./Quiz/SpacedRepetition";
import { useStore } from "../store";

/**
 * Shown when a user lands on Study or Quiz (e.g. via the bottom tab bar) without having
 * picked a concept from the map first. Offers a quick pick from today's due-for-review
 * queue, or a link back to the map to browse the full curriculum.
 */
function NoConceptSelected({ verb }) {
  const { setActiveConcept } = useStore();

  return (
    <section className="no-concept">
      <p className="eyebrow">Nothing selected yet</p>
      <h1>Pick a concept to {verb}</h1>
      <p>Choose from what's due today, or browse the full map to start a new one.</p>
      <SpacedRepetition onSelect={setActiveConcept} />
      <Link className="back" to="/">
        ← Browse the map
      </Link>
    </section>
  );
}

export default NoConceptSelected;
