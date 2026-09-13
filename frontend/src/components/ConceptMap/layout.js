import dagre from "dagre";

const NODE_WIDTH = 210;
const NODE_HEIGHT = 110;

/**
 * Lays out nodes top-to-bottom by prerequisite dependency using dagre, so concepts
 * that unlock later concepts always sit above them with no overlap, regardless of
 * how much title text a node wraps to.
 */
export function layoutNodes(nodes, edges) {
  const graph = new dagre.graphlib.Graph();
  graph.setDefaultEdgeLabel(() => ({}));
  graph.setGraph({ rankdir: "TB", nodesep: 60, ranksep: 90 });

  nodes.forEach((node) => graph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT }));
  edges.forEach((edge) => graph.setEdge(edge.source, edge.target));

  dagre.layout(graph);

  return nodes.map((node) => {
    const { x, y } = graph.node(node.id);
    // dagre gives center coordinates; React Flow expects top-left.
    return { ...node, position: { x: x - NODE_WIDTH / 2, y: y - NODE_HEIGHT / 2 } };
  });
}
