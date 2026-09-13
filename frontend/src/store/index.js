import { create } from "zustand";

export const useStore = create((set) => ({
  phases: [],
  activeConcept: null,
  setPhases: (phases) => set({ phases }),
  setActiveConcept: (concept) => set({ activeConcept: concept }),
  updateMastery: (conceptId, masteryLevel) =>
    set((state) => ({
      phases: state.phases.map((phase) => ({
        ...phase,
        concepts: phase.concepts.map((concept) =>
          concept.id === conceptId ? { ...concept, mastery_level: masteryLevel } : concept
        ),
      })),
    })),
}));
