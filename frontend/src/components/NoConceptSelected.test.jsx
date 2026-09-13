import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import NoConceptSelected from "./NoConceptSelected";
import { useStore } from "../store";

vi.mock("../hooks/api", () => ({
  api: vi.fn().mockResolvedValue({ concepts: [{ id: "cap-theorem", title: "CAP theorem" }] }),
}));

describe("NoConceptSelected", () => {
  it("prompts the user to pick a concept and links back to the map", async () => {
    render(
      <MemoryRouter>
        <NoConceptSelected verb="study" />
      </MemoryRouter>
    );
    expect(screen.getByText("Pick a concept to study")).toBeInTheDocument();
    expect(screen.getByText("← Browse the map")).toBeInTheDocument();
    await waitFor(() => screen.getByText("CAP theorem"));
  });

  it("selecting a due concept sets it as the active concept", async () => {
    render(
      <MemoryRouter>
        <NoConceptSelected verb="quiz" />
      </MemoryRouter>
    );
    const button = await screen.findByText("CAP theorem");
    button.click();
    await waitFor(() => expect(useStore.getState().activeConcept).toEqual({ id: "cap-theorem", title: "CAP theorem" }));
  });
});
