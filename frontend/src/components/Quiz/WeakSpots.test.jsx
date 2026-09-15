import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import WeakSpots from "./WeakSpots";

function jsonResponse(body) {
  return { ok: true, json: async () => body };
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("WeakSpots", () => {
  it("renders nothing while there are no weak spots", async () => {
    global.fetch = vi.fn().mockResolvedValue(jsonResponse({ concepts: [] }));
    const { container } = render(<WeakSpots onSelect={vi.fn()} />);
    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("lists studied-but-weak concepts with their mastery level", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      jsonResponse({ concepts: [{ id: "cap-theorem", title: "CAP theorem", mastery_level: 1 }] })
    );
    render(<WeakSpots onSelect={vi.fn()} />);

    expect(await screen.findByText("CAP theorem")).toBeInTheDocument();
    expect(screen.getByTitle("Mastery 1/5")).toBeInTheDocument();
  });

  it("calls onSelect with the concept when clicked", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      jsonResponse({ concepts: [{ id: "cap-theorem", title: "CAP theorem", mastery_level: 1 }] })
    );
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(<WeakSpots onSelect={onSelect} />);

    await user.click(await screen.findByText("CAP theorem"));
    expect(onSelect).toHaveBeenCalledWith({ id: "cap-theorem", title: "CAP theorem", mastery_level: 1 });
  });
});
