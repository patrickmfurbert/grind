import { useNavigate } from "react-router-dom";
import CodeEditor from "../components/CodeDemo/CodeEditor";
import { useStore } from "../store";

/** Mini demo code environment: run Python/JS/Bash snippets tied to the active concept in an isolated sandbox. */
function CodeLab() {
  const { activeConcept } = useStore();
  const navigate = useNavigate();

  return (
    <section className="code-lab">
      <button className="back" onClick={() => navigate(activeConcept ? "/study" : "/")}>
        ← Back
      </button>
      <h1>Code lab</h1>
      {activeConcept && <p>{activeConcept.title}</p>}
      <CodeEditor />
    </section>
  );
}

export default CodeLab;
