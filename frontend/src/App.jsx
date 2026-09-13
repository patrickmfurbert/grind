import { useEffect, useState } from "react";
import ReactFlow, { Background, Controls } from "reactflow";
import "reactflow/dist/style.css";

const api = (path, options) => fetch(`/api${path}`, options).then((response) => response.json());
const colors = { "Phase 1": "#2563eb", "Phase 2": "#7c3aed", "Phase 2.5": "#9333ea", "Phase 3": "#0891b2", "Phase 4": "#d97706", "Phase 5": "#dc2626" };

function Dashboard({ phases, selectConcept }) {
  const concepts = phases.flatMap((phase) => phase.concepts);
  const nodes = concepts.map((concept, index) => ({ id: concept.id, position: { x: (index % 2) * 230, y: Math.floor(index / 2) * 130 }, data: { label: <button onClick={() => selectConcept(concept)} className="node" style={{ borderColor: colors[concept.phase] }}><small>{concept.phase}</small><strong>{concept.title}</strong><span>{"★".repeat(concept.mastery_level)}{"☆".repeat(5 - concept.mastery_level)}</span></button> } }));
  const edges = concepts.flatMap((concept) => concept.prerequisites.map((source) => ({ id: `${source}-${concept.id}`, source, target: concept.id })));
  return <section className="dashboard"><header><p className="eyebrow">GRIND</p><h1>Own the room.</h1><p>Distributed systems, AI, and system design through deliberate practice.</p></header><div className="map"><ReactFlow nodes={nodes} edges={edges} fitView nodesDraggable={false}><Background /><Controls /></ReactFlow></div></section>;
}

function Study({ concept, back }) {
  const [messages, setMessages] = useState([{ role: "assistant", content: `Let's start with why ${concept.title} exists. What problem do you think it solves?` }]);
  const [input, setInput] = useState("");
  async function send(event) {
    event.preventDefault(); if (!input.trim()) return;
    const history = messages.map(({ role, content }) => ({ role, content }));
    setMessages([...messages, { role: "user", content: input }]); setInput("");
    const response = await fetch("/api/tutor/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ concept_id: concept.id, message: input, conversation_history: history }) });
    const reader = response.body.getReader(); const decoder = new TextDecoder(); let text = "";
    setMessages((items) => [...items, { role: "assistant", content: "" }]);
    while (true) { const { value, done } = await reader.read(); if (done) break; for (const line of decoder.decode(value).split("\n")) if (line.startsWith("data: {")) { text += JSON.parse(line.slice(6)).token; setMessages((items) => [...items.slice(0, -1), { role: "assistant", content: text }]); } }
  }
  return <section className="study"><button className="back" onClick={back}>← Map</button><p className="eyebrow">{concept.phase}</p><h1>{concept.title}</h1><p>{concept.description}</p><div className="chat">{messages.map((message, index) => <div key={index} className={`message ${message.role}`}>{message.content}</div>)}</div><form onSubmit={send}><input value={input} onChange={(event) => setInput(event.target.value)} placeholder="Defend your answer..." /><button>Send</button></form></section>;
}

function App() {
  const [phases, setPhases] = useState([]); const [concept, setConcept] = useState(null);
  useEffect(() => { api("/curriculum/phases").then((data) => setPhases(data.phases)); }, []);
  return <main>{concept ? <Study concept={concept} back={() => setConcept(null)} /> : <Dashboard phases={phases} selectConcept={setConcept} />}</main>;
}
export default App;
