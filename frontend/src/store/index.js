import { create } from "zustand";
import { persist } from "zustand/middleware";

// Persisted to localStorage so a page refresh (or deep link) mid-study doesn't lose the
// selected concept and bounce the user back to the map.
export const useStore = create(
  persist(
    (set) => ({
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
    }),
    {
      name: "grind-store",
      // Only persist the active concept, not the full curriculum tree (that's refetched on load).
      partialize: (state) => ({ activeConcept: state.activeConcept }),
    }
  )
);
