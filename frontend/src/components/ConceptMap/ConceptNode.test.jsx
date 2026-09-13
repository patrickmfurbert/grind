import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

// ConceptNode only uses Handle for connection anchors; stub it so the node can render
// standalone without a full ReactFlowProvider (which needs real layout/measurement).
vi.mock("reactflow", () => ({
  Handle: () => null,
  Position: { Top: "top", Bottom: "bottom" },
}));

const { default: ConceptNode } = await import("../../components/ConceptMap/ConceptNode");

const concept = { id: "cap-theorem", phase: "Phase 1", title: "CAP theorem", mastery_level: 2 };

describe("ConceptNode", () => {
  it("renders the concept title, phase, and mastery stars", () => {
    render(<ConceptNode data={{ concept, locked: false, onSelect: vi.fn() }} />);
    expect(screen.getByText("CAP theorem")).toBeInTheDocument();
    expect(screen.getByText("Phase 1")).toBeInTheDocument();
    expect(screen.getByText("★★☆☆☆")).toBeInTheDocument();
  });

  it("calls onSelect when an unlocked node is clicked", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(<ConceptNode data={{ concept, locked: false, onSelect }} />);
    await user.click(screen.getByRole("button"));
    expect(onSelect).toHaveBeenCalledWith(concept);
  });

  it("disables the node and shows a lock icon when locked", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(<ConceptNode data={{ concept, locked: true, onSelect }} />);
    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
    expect(button).toHaveTextContent("🔒");
    await user.click(button);
    expect(onSelect).not.toHaveBeenCalled();
  });
});
