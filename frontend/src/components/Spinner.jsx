/** Small inline spinning ring — used anywhere we're waiting on an LLM call (quiz
 * generation, grading, hints) so those states read as "working" instead of static. */
function Spinner() {
  return <span className="spinner" aria-hidden="true" />;
}

export default Spinner;
