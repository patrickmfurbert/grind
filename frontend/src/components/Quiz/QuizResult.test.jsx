import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import QuizResult from "../../components/Quiz/QuizResult";

describe("QuizResult", () => {
  it("renders nothing when there is no result yet", () => {
    const { container } = render(<QuizResult result={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows an on-track message for a correct result", () => {
    render(
      <QuizResult
        result={{ correct: true, explanation: "Nice trade-off analysis.", next_review_date: "2026-01-01T00:00:00Z" }}
      />
    );
    expect(screen.getByText("On track")).toBeInTheDocument();
    expect(screen.getByText("Nice trade-off analysis.")).toBeInTheDocument();
  });

  it("shows a review-needed message for an incorrect result", () => {
    render(
      <QuizResult result={{ correct: false, explanation: "Revisit the trade-offs.", next_review_date: "2026-01-01T00:00:00Z" }} />
    );
    expect(screen.getByText("Review needed")).toBeInTheDocument();
  });
});
