import ReactFlow, { Background, Controls } from "reactflow";
import "reactflow/dist/style.css";
import ConceptNode from "./ConceptNode";
import { buildEdge } from "./ConceptEdge";

const nodeTypes = { concept: ConceptNode };

/** Renders all curriculum concepts as a React Flow graph, locking nodes whose prerequisites are incomplete. */
function ConceptMap({ phases, onSelect }) {
  const concepts = phases.flatMap((phase) => phase.concepts);
  const masteryById = Object.fromEntries(concepts.map((concept) => [concept.id, concept.mastery_level]));

  const nodes = concepts.map((concept, index) => ({
    id: concept.id,
    type: "concept",
    position: { x: (index % 3) * 240, y: Math.floor(index / 3) * 150 },
    data: {
      concept,
      locked: concept.prerequisites.some((id) => (masteryById[id] ?? 0) === 0),
      onSelect,
    },
  }));

  const edges = concepts.flatMap((concept) => concept.prerequisites.map((sourceId) => buildEdge(sourceId, concept.id)));

  return (
    <div className="map">
      <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView nodesDraggable={false}>
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}

export default ConceptMap;
