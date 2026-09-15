const PHASE_COLORS = {
  "Phase 1": "#2563eb",
  "Phase 1.5": "#4f46e5",
  "Phase 2": "#7c3aed",
  "Phase 2.5": "#9333ea",
  "Phase 3": "#0891b2",
  "Phase 4": "#d97706",
  "Phase 5": "#dc2626",
  "Phase 6": "#16a34a",
};

export function phaseColor(phase) {
  return PHASE_COLORS[phase] ?? "#64748b";
}
