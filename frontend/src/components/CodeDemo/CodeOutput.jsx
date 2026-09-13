/** Displays stdout/stderr and execution time returned from the code execution endpoint. */
function CodeOutput({ result }) {
  if (!result) return null;
  return (
    <div className="code-output">
      {result.output && <pre className="stdout">{result.output}</pre>}
      {result.error && <pre className="stderr">{result.error}</pre>}
      <small>{result.execution_time}s</small>
    </div>
  );
}

export default CodeOutput;
