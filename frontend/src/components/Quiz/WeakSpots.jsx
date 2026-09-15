import { useEffect, useState } from "react";
import MasteryBadge from "../Progress/MasteryBadge";
import { api } from "../../hooks/api";

/** Lists studied-but-not-yet-mastered concepts, weakest first, so it's obvious where to
 * focus next instead of only seeing what the spaced-repetition schedule says is due. */
function WeakSpots({ onSelect }) {
  const [weak, setWeak] = useState([]);

  useEffect(() => {
    api("/progress/weak-spots").then((data) => setWeak(data.concepts));
  }, []);

  if (!weak.length) return null;

  return (
    <div className="weak-spots">
      <h2>Weak spots</h2>
      <ul>
        {weak.map((concept) => (
          <li key={concept.id}>
            <button onClick={() => onSelect(concept)}>{concept.title}</button>
            <MasteryBadge level={concept.mastery_level} />
          </li>
        ))}
      </ul>
    </div>
  );
}

export default WeakSpots;
