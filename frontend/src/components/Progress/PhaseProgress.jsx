/** Summary bar: overall completion percent, per-phase average mastery, and study streak. */
function PhaseProgress({ summary }) {
  if (!summary) return null;
  return (
    <div className="phase-progress">
      <div className="stat">
        <strong>{summary.overall_pct}%</strong>
        <span>Overall</span>
      </div>
      <div className="stat">
        <strong>{summary.streak}</strong>
        <span>Day streak</span>
      </div>
      {summary.by_phase.map((phase) => (
        <div className="stat" key={phase.phase}>
          <strong>{phase.mastery ? phase.mastery.toFixed(1) : "0.0"}</strong>
          <span>{phase.phase}</span>
        </div>
      ))}
    </div>
  );
}

export default PhaseProgress;
