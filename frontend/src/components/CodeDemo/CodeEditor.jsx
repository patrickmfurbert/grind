import Editor from "@monaco-editor/react";
import { useState } from "react";
import { api } from "../../hooks/api";
import CodeOutput from "./CodeOutput";

const TEMPLATES = {
  python: "print('hello from grind')\n",
  javascript: "console.log('hello from grind');\n",
  bash: "echo 'hello from grind'\n",
};

const LANGUAGES = Object.keys(TEMPLATES);

/** Monaco-based mini code demo editor: pick a language, run it against the backend sandbox, see output. */
function CodeEditor({ initialLanguage = "python", initialCode }) {
  const [language, setLanguage] = useState(initialLanguage);
  const [code, setCode] = useState(initialCode ?? TEMPLATES[initialLanguage]);
  const [result, setResult] = useState(null);
  const [running, setRunning] = useState(false);

  function changeLanguage(next) {
    setLanguage(next);
    setCode(TEMPLATES[next]);
    setResult(null);
  }

  async function run() {
    setRunning(true);
    try {
      setResult(await api("/code/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language, code }),
      }));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="code-editor">
      <div className="toolbar">
        <select value={language} onChange={(event) => changeLanguage(event.target.value)}>
          {LANGUAGES.map((lang) => (
            <option key={lang} value={lang}>
              {lang}
            </option>
          ))}
        </select>
        <button onClick={run} disabled={running}>
          {running ? "Running…" : "Run"}
        </button>
      </div>
      <Editor
        height="40vh"
        language={language === "bash" ? "shell" : language}
        theme="vs-dark"
        value={code}
        onChange={(value) => setCode(value ?? "")}
        options={{ minimap: { enabled: false }, fontSize: 14 }}
      />
      <CodeOutput result={result} />
    </div>
  );
}

export default CodeEditor;
