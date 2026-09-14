import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import ConceptMap from "../components/ConceptMap/ConceptMap";
import PhaseProgress from "../components/Progress/PhaseProgress";
import { useProgress } from "../hooks/useProgress";
import { useStore } from "../store";
import { api } from "../hooks/api";

/** Home page: overall progress summary plus the visual concept map for navigating into study. */
function Dashboard() {
  const { phases, setPhases, setActiveConcept } = useStore();
  const { summary } = useProgress();
  const navigate = useNavigate();

  useEffect(() => {
    api("/curriculum/phases").then((data) => setPhases(data.phases));
  }, [setPhases]);

  function select(concept) {
    setActiveConcept(concept);
    navigate("/study");
  }

  return (
    <section className="dashboard">
      <header>
        <p className="eyebrow">GRIND</p>
        <h1>Map</h1>
        <p>Distributed systems, AI, and system design through deliberate practice.</p>
      </header>
      <PhaseProgress summary={summary} />
      <ConceptMap phases={phases} onSelect={select} />
    </section>
  );
}

export default Dashboard;
