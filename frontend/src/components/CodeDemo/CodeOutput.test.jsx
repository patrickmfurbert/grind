import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import CodeOutput from "../../components/CodeDemo/CodeOutput";

describe("CodeOutput", () => {
  it("renders nothing before any execution result exists", () => {
    const { container } = render(<CodeOutput result={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders stdout and execution time", () => {
    render(<CodeOutput result={{ output: "42\n", error: "", execution_time: 0.12 }} />);
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("0.12s")).toBeInTheDocument();
  });

  it("renders stderr when present", () => {
    render(<CodeOutput result={{ output: "", error: "boom", execution_time: 0.01 }} />);
    expect(screen.getByText("boom")).toBeInTheDocument();
  });
});
