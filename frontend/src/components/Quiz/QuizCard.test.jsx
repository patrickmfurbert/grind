import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import QuizCard from "../../components/Quiz/QuizCard";

const freeResponseQuestion = { id: "q1", type: "free_response", prompt: "Why does this concept exist?" };
const mcqQuestion = {
  id: "q2",
  type: "multiple_choice",
  prompt: "Which best describes this concept?",
  options: ["Scale", "Style", "Speed", "Silence"],
};

describe("QuizCard", () => {
  it("renders the question prompt", () => {
    render(<QuizCard question={freeResponseQuestion} onSubmit={vi.fn()} />);
    expect(screen.getByText("Why does this concept exist?")).toBeInTheDocument();
  });

  it("submits a free-response answer with the question id and type", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<QuizCard question={freeResponseQuestion} onSubmit={onSubmit} />);

    await user.type(screen.getByPlaceholderText("Your answer..."), "Because failures are inevitable at scale.");
    await user.click(screen.getByText("Submit"));

    expect(onSubmit).toHaveBeenCalledWith("q1", "Because failures are inevitable at scale.");
  });

  it("renders multiple choice options as radio buttons and submits the selected option", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<QuizCard question={mcqQuestion} onSubmit={onSubmit} />);

    expect(screen.getByText("Scale")).toBeInTheDocument();
    await user.click(screen.getByText("Scale"));
    await user.click(screen.getByText("Submit"));

    expect(onSubmit).toHaveBeenCalledWith("q2", "Scale");
  });

  it("disables submit until an answer is selected", () => {
    render(<QuizCard question={mcqQuestion} onSubmit={vi.fn()} />);
    expect(screen.getByText("Submit")).toBeDisabled();
  });

  it("shows a grading state and disables submit while grading is in progress", () => {
    render(<QuizCard question={freeResponseQuestion} onSubmit={vi.fn()} grading />);
    expect(screen.getByText("Grading…")).toBeInTheDocument();
    expect(screen.getByText("Grading…")).toBeDisabled();
  });
});
