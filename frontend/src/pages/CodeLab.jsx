import CodeEditor from "../components/CodeDemo/CodeEditor";
import { useStore } from "../store";

/** Mini demo code environment: run Python/JS/Bash snippets tied to the active concept in an isolated sandbox. */
function CodeLab() {
  const { activeConcept } = useStore();

  return (
    <section className="code-lab">
      <h1>Code lab</h1>
      {activeConcept && <p>{activeConcept.title}</p>}
      <CodeEditor />
    </section>
  );
}

export default CodeLab;
