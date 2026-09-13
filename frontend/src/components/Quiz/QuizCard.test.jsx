import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import QuizCard from "../../components/Quiz/QuizCard";

const question = { id: "q1", type: "comprehension", prompt: "Why does this concept exist?" };

describe("QuizCard", () => {
  it("renders the question prompt", () => {
    render(<QuizCard question={question} onSubmit={vi.fn()} />);
    expect(screen.getByText("Why does this concept exist?")).toBeInTheDocument();
  });

  it("submits the answer, quiz type, and confidence score", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<QuizCard question={question} onSubmit={onSubmit} />);

    await user.type(screen.getByPlaceholderText("Your answer..."), "Because failures are inevitable at scale.");
    await user.click(screen.getByText("Submit"));

    expect(onSubmit).toHaveBeenCalledWith(
      "q1",
      "Because failures are inevitable at scale.",
      "comprehension",
      3
    );
  });
});
