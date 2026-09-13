import { Handle, Position } from "reactflow";
import { phaseColor } from "./phaseColors";

/** A single concept node showing phase, title, mastery stars, and a lock if prerequisites are unmet. */
function ConceptNode({ data }) {
  const { concept, locked, onSelect } = data;
  return (
    <button
      className="node"
      style={{ borderColor: phaseColor(concept.phase) }}
      onClick={() => !locked && onSelect(concept)}
      disabled={locked}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <small>{concept.phase}</small>
      <strong>
        {locked ? "🔒 " : ""}
        {concept.title}
      </strong>
      <span>
        {"★".repeat(concept.mastery_level)}
        {"☆".repeat(5 - concept.mastery_level)}
      </span>
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </button>
  );
}

export default ConceptNode;
