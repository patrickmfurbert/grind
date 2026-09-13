import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MasteryBadge from "../../components/Progress/MasteryBadge";

describe("MasteryBadge", () => {
  it("renders filled stars equal to the mastery level", () => {
    render(<MasteryBadge level={3} />);
    expect(screen.getByTitle("Mastery 3/5")).toHaveTextContent("★★★☆☆");
  });

  it("renders all empty stars at level zero", () => {
    render(<MasteryBadge level={0} />);
    expect(screen.getByTitle("Mastery 0/5")).toHaveTextContent("☆☆☆☆☆");
  });

  it("renders all filled stars at level five", () => {
    render(<MasteryBadge level={5} />);
    expect(screen.getByTitle("Mastery 5/5")).toHaveTextContent("★★★★★");
  });
});
