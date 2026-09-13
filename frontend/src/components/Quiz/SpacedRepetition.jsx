import { useEffect, useState } from "react";
import { api } from "../../hooks/api";

/** Lists concepts due for spaced-repetition review today, per the SM-2 schedule. */
function SpacedRepetition({ onSelect }) {
  const [due, setDue] = useState([]);

  useEffect(() => {
    api("/quiz/due-today").then((data) => setDue(data.concepts));
  }, []);

  if (!due.length) return <p className="due-today empty">Nothing due today. Keep grinding.</p>;

  return (
    <div className="due-today">
      <h2>Due today</h2>
      <ul>
        {due.map((concept) => (
          <li key={concept.id}>
            <button onClick={() => onSelect(concept)}>{concept.title}</button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default SpacedRepetition;
