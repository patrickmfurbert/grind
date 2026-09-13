import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PhaseProgress from "../../components/Progress/PhaseProgress";

const summary = {
  overall_pct: 42,
  streak: 3,
  by_phase: [{ phase: "Phase 1", mastery: 2.5 }, { phase: "Phase 2", mastery: 0 }],
};

describe("PhaseProgress", () => {
  it("renders nothing when summary is not yet loaded", () => {
    const { container } = render(<PhaseProgress summary={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows overall percentage and streak", () => {
    render(<PhaseProgress summary={summary} />);
    expect(screen.getByText("42%")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("Day streak")).toBeInTheDocument();
  });

  it("shows a stat per phase with mastery formatted to one decimal", () => {
    render(<PhaseProgress summary={summary} />);
    expect(screen.getByText("2.5")).toBeInTheDocument();
    expect(screen.getByText("0.0")).toBeInTheDocument();
  });
});
