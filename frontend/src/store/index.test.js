import { describe, expect, it } from "vitest";
import { useStore } from "./index";

const phases = [
  {
    name: "Phase 1",
    concepts: [
      { id: "why-distributed-systems-exist", mastery_level: 0 },
      { id: "failure-modes", mastery_level: 1 },
    ],
  },
];

describe("useStore", () => {
  it("starts with no phases and no active concept", () => {
    expect(useStore.getState().phases).toEqual([]);
    expect(useStore.getState().activeConcept).toBeNull();
  });

  it("setPhases replaces the phases array", () => {
    useStore.getState().setPhases(phases);
    expect(useStore.getState().phases).toEqual(phases);
  });

  it("setActiveConcept stores the selected concept", () => {
    const concept = { id: "cap-theorem", title: "CAP theorem" };
    useStore.getState().setActiveConcept(concept);
    expect(useStore.getState().activeConcept).toEqual(concept);
  });

  it("updateMastery updates only the matching concept across all phases", () => {
    useStore.getState().setPhases(phases);
    useStore.getState().updateMastery("failure-modes", 4);
    const updated = useStore.getState().phases[0].concepts;
    expect(updated.find((c) => c.id === "failure-modes").mastery_level).toBe(4);
    expect(updated.find((c) => c.id === "why-distributed-systems-exist").mastery_level).toBe(0);
  });
});
