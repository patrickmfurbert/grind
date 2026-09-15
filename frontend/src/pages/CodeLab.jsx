import { useEffect, useState } from "react";
import CodeEditor from "../components/CodeDemo/CodeEditor";
import { api } from "../hooks/api";
import { useStore } from "../store";

/** Mini demo code environment: run Python/JS/Bash snippets tied to the active concept in an isolated sandbox. */
function CodeLab() {
  const { activeConcept } = useStore();
  const [demos, setDemos] = useState([]);
  const [selectedDemo, setSelectedDemo] = useState(null);

  useEffect(() => {
    setSelectedDemo(null);
    if (!activeConcept) {
      setDemos([]);
      return;
    }
    api(`/curriculum/code-demos/${activeConcept.id}`).then((data) => setDemos(data.code_demos || []));
  }, [activeConcept]);

  const demo = selectedDemo !== null ? demos[selectedDemo] : null;

  return (
    <section className="code-lab">
      <h1>Code lab</h1>
      {activeConcept && <p>{activeConcept.title}</p>}
      {demos.length > 0 && (
        <div className="code-demos">
          {demos.map((item, index) => (
            <button key={item.title} className={index === selectedDemo ? "active" : ""} onClick={() => setSelectedDemo(index)}>
              {item.title}
            </button>
          ))}
        </div>
      )}
      <CodeEditor key={demo ? demo.title : "default"} initialLanguage={demo?.language} initialCode={demo?.starter} />
    </section>
  );
}

export default CodeLab;
