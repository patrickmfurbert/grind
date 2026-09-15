import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import TutorChat from "./TutorChat";
import { useTutor } from "../../hooks/useTutor";

vi.mock("../../hooks/useTutor");

const CONCEPT = { id: "cap-theorem", title: "CAP theorem" };

function stubTutor(overrides = {}) {
  useTutor.mockReturnValue({
    messages: [],
    send: vi.fn(),
    streaming: false,
    loadingHistory: false,
    clearHistory: vi.fn(),
    masteryUpdate: null,
    ...overrides,
  });
}

describe("TutorChat", () => {
  it("shows an honest mastery-update note only when the hook reports a genuine update", () => {
    stubTutor({ masteryUpdate: { level: 3 } });
    render(<TutorChat concept={CONCEPT} />);
    expect(screen.getByText(/mastery updated to 3\/5/i)).toBeInTheDocument();
  });

  it("renders no mastery note when nothing has been updated", () => {
    stubTutor({ masteryUpdate: null });
    render(<TutorChat concept={CONCEPT} />);
    expect(screen.queryByText(/mastery updated/i)).not.toBeInTheDocument();
  });
});
