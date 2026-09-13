import { MarkerType } from "reactflow";

/** Builds a directed edge between a prerequisite concept and its dependent concept. */
export function buildEdge(sourceId, targetId) {
  return {
    id: `${sourceId}-${targetId}`,
    source: sourceId,
    target: targetId,
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { stroke: "#334155" },
  };
}
