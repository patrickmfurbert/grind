import ReactFlow, { Background, Controls } from "reactflow";
import "reactflow/dist/style.css";
import ConceptNode from "./ConceptNode";
import { buildEdge } from "./ConceptEdge";
import { layoutNodes } from "./layout";

const nodeTypes = { concept: ConceptNode };

/** Renders all curriculum concepts as a React Flow graph, locking nodes whose prerequisites are incomplete. */
function ConceptMap({ phases, onSelect }) {
  const concepts = phases.flatMap((phase) => phase.concepts);
  const masteryById = Object.fromEntries(concepts.map((concept) => [concept.id, concept.mastery_level]));

  const unpositionedNodes = concepts.map((concept) => ({
    id: concept.id,
    type: "concept",
    position: { x: 0, y: 0 },
    data: {
      concept,
      locked: concept.prerequisites.some((id) => (masteryById[id] ?? 0) === 0),
      onSelect,
    },
  }));

  const edges = concepts.flatMap((concept) => concept.prerequisites.map((sourceId) => buildEdge(sourceId, concept.id)));

  // Auto-layout by prerequisite dependency (top-to-bottom) so nodes never overlap,
  // regardless of how tall a node's wrapped title text renders.
  const nodes = layoutNodes(unpositionedNodes, edges);

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
