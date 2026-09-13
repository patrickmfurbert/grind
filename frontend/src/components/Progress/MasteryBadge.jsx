/** Stars indicator for a concept's mastery level (0-5). */
function MasteryBadge({ level }) {
  return (
    <span className="mastery-badge" title={`Mastery ${level}/5`}>
      {"★".repeat(level)}
      {"☆".repeat(5 - level)}
    </span>
  );
}

export default MasteryBadge;
